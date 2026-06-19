from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
from datetime import datetime

from app.db.database import get_db
from app.models.models import Category, Transaction, User
from app.schemas.schemas import TransactionCategoryCorrectionRequest, TransactionCreate, TransactionResponse
from app.api.auth import get_current_user
from app.services.categorization import (
    categorize_transaction,
    learn_user_category_preference,
)
from app.services.learning_service import save_category_correction
from app.services.merchant_extractor_service import extract_transaction_merchant
from app.services.friend_service import auto_attach_transaction_if_friend
from app.services.friend_service import attach_transaction_to_friend, create_friend
from app.services.friend_detection_service import extract_friend_name_from_text
from app.services.transaction_type_service import normalize_transaction_type

router = APIRouter(prefix="/transactions", tags=["transactions"])


def ensure_category_exists(db: Session, category_id: Optional[int]) -> None:
    if category_id is None:
        return

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected category does not exist"
        )


def parse_date_filter(value: Optional[str], field_name: str) -> Optional[datetime]:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a valid ISO date"
        )


def review_status_from_result(category_confidence: float, categorization_method: str) -> tuple[str, bool]:
    """Convert categorization metadata into the review fields stored on transactions."""
    needs_review = categorization_method == "needs_review" or category_confidence < 0.80
    return ("needs_review" if needs_review else "approved"), needs_review


def sync_friend_if_friends_category(
    db: Session,
    user_id: int,
    transaction: Transaction,
    category_id: int,
) -> None:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category or category.name.strip().lower() != "friends":
        return

    friend_name = extract_friend_name_from_text(
        transaction.description,
        transaction.extracted_merchant or transaction.merchant,
    )
    if not friend_name:
        friend_name = transaction.extracted_merchant or transaction.merchant or transaction.description
    if not friend_name:
        return

    friend = create_friend(db, user_id, friend_name)
    attach_transaction_to_friend(db, user_id, friend, transaction)


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category_id = transaction_data.category_id
    category_confidence = 1.0
    categorization_method = "manual" if category_id is not None else "needs_review"
    merchant = transaction_data.merchant
    if category_id is None:
        result = categorize_transaction(
            db,
            current_user.id,
            transaction_data.description,
            transaction_data.amount,
            transaction_data.transaction_type,
            transaction_data.merchant,
        )
        category_id = result["category_id"] if isinstance(result["category_id"], int) else None
        category_confidence = float(result["confidence"])
        categorization_method = str(result["method"])
        merchant = str(result.get("merchant") or transaction_data.merchant or "")
        extracted_merchant = str(result.get("merchant") or "").strip() or None
    else:
        ensure_category_exists(db, category_id)
        extracted_merchant = extract_transaction_merchant(transaction_data.description, merchant)
        learn_user_category_preference(
            db,
            current_user.id,
            extracted_merchant,
            category_id,
        )

    final_transaction_type = normalize_transaction_type(
        db,
        transaction_data.transaction_type,
        category_id,
    )
    review_status, is_needs_review = review_status_from_result(category_confidence, categorization_method)

    transaction = Transaction(
        user_id=current_user.id,
        amount=transaction_data.amount,
        category_id=category_id,
        description=transaction_data.description,
        merchant=merchant,
        extracted_merchant=extracted_merchant,
        transaction_type=final_transaction_type,
        date=transaction_data.date,
        category_confidence=category_confidence,
        categorization_method=categorization_method,
        review_status=review_status,
        is_needs_review=is_needs_review,
    )
    db.add(transaction)
    db.flush()
    auto_attach_transaction_if_friend(db, current_user.id, transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=List[TransactionResponse])
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    transaction_type: Optional[str] = None,
    category_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.description.ilike(term),
                Transaction.merchant.ilike(term)
            )
        )

    if transaction_type in {"income", "expense", "savings"}:
        query = query.filter(Transaction.transaction_type == transaction_type)

    if category_id is not None:
        ensure_category_exists(db, category_id)
        query = query.filter(Transaction.category_id == category_id)

    parsed_start = parse_date_filter(start_date, "start_date")
    parsed_end = parse_date_filter(end_date, "end_date")

    if parsed_start:
        query = query.filter(Transaction.date >= parsed_start)

    if parsed_end:
        query = query.filter(Transaction.date <= parsed_end)

    return query.order_by(Transaction.date.desc()).all()


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id,
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    old_category_id = transaction.category_id
    new_category_id = transaction_data.category_id

    if new_category_id is None:
        result = categorize_transaction(
            db,
            current_user.id,
            transaction_data.description,
            transaction_data.amount,
            transaction_data.transaction_type,
            transaction_data.merchant,
        )
        new_category_id = result["category_id"] if isinstance(result["category_id"], int) else None
        transaction.category_confidence = float(result["confidence"])
        transaction.categorization_method = str(result["method"])
        transaction.extracted_merchant = str(result.get("merchant") or "").strip() or None
    else:
        ensure_category_exists(db, new_category_id)
        transaction.category_confidence = 1.0
        transaction.categorization_method = "manual"
        transaction.extracted_merchant = extract_transaction_merchant(transaction_data.description, transaction_data.merchant)
        learn_user_category_preference(
            db,
            current_user.id,
            transaction.extracted_merchant,
            new_category_id,
        )

    if old_category_id != new_category_id and new_category_id is not None:
        save_category_correction(
            db,
            current_user.id,
            transaction.id,
            old_category_id,
            new_category_id,
            correction_source="manual",
        )

    transaction.amount = transaction_data.amount
    transaction.category_id = new_category_id
    transaction.description = transaction_data.description
    transaction.merchant = transaction.extracted_merchant or transaction_data.merchant
    transaction.transaction_type = normalize_transaction_type(
        db,
        transaction_data.transaction_type,
        new_category_id,
    )
    transaction.date = transaction_data.date
    transaction.review_status, transaction.is_needs_review = review_status_from_result(
        transaction.category_confidence or 0.30,
        transaction.categorization_method or "needs_review",
    )

    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/review", response_model=List[TransactionResponse])
def get_transactions_for_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            or_(
                Transaction.review_status == "needs_review",
                Transaction.is_needs_review == True,  # noqa: E712
                Transaction.category_confidence < 0.80,
            ),
        )
        .order_by(Transaction.date.desc())
        .all()
    )


@router.post("/{transaction_id}/correct-category", response_model=TransactionResponse)
def correct_transaction_category_from_transactions(
    transaction_id: int,
    correction_data: TransactionCategoryCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id,
    ).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    ensure_category_exists(db, correction_data.category_id)
    save_category_correction(db, current_user.id, transaction.id, transaction.category_id, correction_data.category_id)
    transaction.category_id = correction_data.category_id
    transaction.transaction_type = normalize_transaction_type(
        db,
        transaction.transaction_type,
        correction_data.category_id,
    )
    transaction.category_confidence = 1.0
    transaction.categorization_method = "manual"
    transaction.review_status = "approved"
    transaction.is_needs_review = False
    sync_friend_if_friends_category(db, current_user.id, transaction, correction_data.category_id)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id,
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    db.delete(transaction)
    db.commit()
