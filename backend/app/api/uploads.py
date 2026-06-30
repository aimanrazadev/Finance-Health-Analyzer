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
from app.services.file_parser_service import MAX_UPLOAD_SIZE_BYTES, parse_statement_file, validate_statement_file
from app.services.friend_service import auto_attach_transaction_if_friend, create_or_update_friend_from_transaction, is_friends_category
from app.services.import_profile_service import save_import_profile_from_columns
from app.services.merchant_extractor_service import extract_transaction_merchant
from app.services.transaction_type_service import normalize_transaction_type

router = APIRouter(tags=["statement upload"])


@router.post("/uploads/preview", response_model=UploadPreviewResponse)
@router.post("/upload/preview", response_model=UploadPreviewResponse, include_in_schema=False)
async def preview_statement_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    file_name = file.filename or "statement.pdf"
    parsed = parse_statement_file(file_name, content, db, user_id=current_user.id)
    import_profile = parsed.get("import_profile") or {}
    return UploadPreviewResponse(
        file_name=file_name,
        file_size=len(content),
        file_type=parsed["file_type"],
        import_profile_id=import_profile.get("id"),
        import_profile_name=import_profile.get("name"),
        import_confidence=import_profile.get("confidence") or 0,
        bank_name=import_profile.get("bank_name"),
        opening_balance=parsed.get("opening_balance"),
        closing_balance=parsed.get("closing_balance"),
        column_mapping=import_profile.get("column_mapping") or {},
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
    file_type = "pdf"
    if upload_data.column_mapping:
        save_import_profile_from_columns(
            db,
            current_user.id,
            upload_data.bank_name or upload_data.file_name,
            file_type,
            list(upload_data.column_mapping.keys()),
        )

    uploaded_file = UploadedFile(
        user_id=current_user.id,
        filename=upload_data.file_name,
        file_path=f"confirmed-import://{upload_data.file_name}",
        file_type=file_type,
        file_size=upload_data.file_size,
        opening_balance=upload_data.opening_balance,
        closing_balance=upload_data.closing_balance,
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

        final_transaction_type = normalize_transaction_type(db, row.transaction_type, row.category_id)

        transaction = Transaction(
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
            transaction_type=final_transaction_type,
            date=row.date or row.transaction_date,
            uploaded_file_id=uploaded_file.id,
            source="pdf",
            payment_method=None,
            category_confidence=row.category_confidence or 0.30,
            categorization_method=row.categorization_method or "needs_review",
            review_status="approved" if (row.category_confidence or 0.30) >= 0.80 and (row.categorization_method or "needs_review") != "needs_review" else "needs_review",
            is_needs_review=(row.category_confidence or 0.30) < 0.80 or (row.categorization_method or "needs_review") == "needs_review",
        )
        db.add(transaction)
        db.flush()
        if row.category_id is not None and is_friends_category(db, row.category_id):
            create_or_update_friend_from_transaction(db, current_user.id, transaction)
        else:
            auto_attach_transaction_if_friend(db, current_user.id, transaction)
        transactions.append(transaction)

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
