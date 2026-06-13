from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import List

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Transaction, UploadedFile, User
from app.schemas.schemas import (
    UploadConfirmRequest,
    UploadConfirmResponse,
    UploadedFileResponse,
    UploadPreviewResponse,
)
from app.services.file_parser_service import detect_file_type, parse_statement_file, validate_statement_file
from app.services.merchant_extractor_service import extract_transaction_merchant

router = APIRouter(tags=["statement upload"])


@router.post("/uploads/preview", response_model=UploadPreviewResponse)
@router.post("/upload/preview", response_model=UploadPreviewResponse, include_in_schema=False)
async def preview_statement_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    file_name = file.filename or "statement"
    parsed = parse_statement_file(file_name, content, db, user_id=current_user.id)
    return UploadPreviewResponse(
        file_name=file_name,
        file_size=len(content),
        file_type=parsed["file_type"],
        total_rows=parsed["total_rows"],
        successful_rows=parsed["successful_rows"],
        valid_rows=parsed["successful_rows"],
        failed_rows=parsed["failed_rows"],
        rows=parsed["transactions"],
        failed_items=parsed["failed_items"],
        errors=[item["error"] for item in parsed["failed_items"]],
    )


def _duplicate_exists(db: Session, user_id: int, row) -> bool:
    reference_no = row.reference_no.strip() if row.reference_no else None
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date == (row.date or row.transaction_date),
        Transaction.amount == row.amount,
        Transaction.description == row.description,
    )
    if reference_no:
        query = query.filter(Transaction.reference_no == reference_no)
    else:
        query = query.filter(Transaction.reference_no.is_(None))
    return query.first() is not None


@router.post("/uploads/confirm", response_model=UploadConfirmResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload/confirm", response_model=UploadConfirmResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def confirm_statement_upload(
    upload_data: UploadConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    validate_statement_file(upload_data.file_name, upload_data.file_size)
    file_type = upload_data.file_type or detect_file_type(upload_data.file_name)

    uploaded_file = UploadedFile(
        user_id=current_user.id,
        filename=upload_data.file_name,
        file_path=f"confirmed-import://{upload_data.file_name}",
        file_type=file_type,
        file_size=upload_data.file_size,
        upload_status="processed",
        total_rows=upload_data.total_rows or len(upload_data.rows),
        successful_rows=0,
        failed_rows=upload_data.failed_rows or 0,
        transaction_count=0,
    )
    db.add(uploaded_file)
    db.flush()

    transactions = []
    skipped_duplicates = 0
    for row in upload_data.rows:
        if _duplicate_exists(db, current_user.id, row):
            skipped_duplicates += 1
            continue
        merchant_name = extract_transaction_merchant(row.description, row.extracted_merchant or row.merchant or row.merchant_name)

        transactions.append(
            Transaction(
                user_id=current_user.id,
                amount=row.amount,
                category_id=row.category_id,
                description=row.description,
                merchant=merchant_name,
                extracted_merchant=merchant_name,
                reference_no=row.reference_no,
                withdrawal_amount=row.withdrawal_amount,
                deposit_amount=row.deposit_amount,
                balance=row.balance,
                transaction_type=row.transaction_type,
                date=row.date or row.transaction_date,
                uploaded_file_id=uploaded_file.id,
                source=row.source or file_type,
                payment_method=None,
                is_recurring=False,
                category_confidence=row.category_confidence or 0.30,
                categorization_method=row.categorization_method or "needs_review",
                review_status="approved" if (row.category_confidence or 0.30) >= 0.80 and (row.categorization_method or "needs_review") != "needs_review" else "needs_review",
                is_needs_review=(row.category_confidence or 0.30) < 0.80 or (row.categorization_method or "needs_review") == "needs_review",
            )
        )

    if transactions:
        db.add_all(transactions)
    uploaded_file.transaction_count = len(transactions)
    uploaded_file.successful_rows = len(transactions)
    db.commit()
    db.refresh(uploaded_file)

    return UploadConfirmResponse(
        uploaded_file_id=uploaded_file.id,
        saved_transactions=len(transactions),
        skipped_duplicates=skipped_duplicates,
        message=f"Saved {len(transactions)} transactions from {upload_data.file_name}.",
    )


@router.get("/uploads/history", response_model=List[UploadedFileResponse])
@router.get("/upload/history", response_model=List[UploadedFileResponse], include_in_schema=False)
def get_upload_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(UploadedFile)
        .filter(UploadedFile.user_id == current_user.id)
        .order_by(UploadedFile.upload_date.desc())
        .all()
    )


@router.delete("/uploads/{uploaded_file_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/upload/{uploaded_file_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def delete_uploaded_statement(
    uploaded_file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uploaded_file = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id == uploaded_file_id,
            UploadedFile.user_id == current_user.id,
        )
        .first()
    )
    if not uploaded_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded statement not found",
        )

    db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.uploaded_file_id == uploaded_file.id,
    ).delete(synchronize_session=False)
    db.delete(uploaded_file)
    db.commit()
