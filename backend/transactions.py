from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
from datetime import datetime

from database import get_db
from models import Category, CategoryCorrection, Transaction, User
from schemas import TransactionCreate, TransactionResponse
from auth import get_current_user
from services.categorization import (
    categorize_transaction,
    learn_user_category_preference,
)

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
    else:
        ensure_category_exists(db, category_id)
        learn_user_category_preference(
            db,
            current_user.id,
            merchant,
            category_id,
        )

    transaction = Transaction(
        user_id=current_user.id,
        amount=transaction_data.amount,
        category_id=category_id,
        description=transaction_data.description,
        merchant=merchant,
        transaction_type=transaction_data.transaction_type,
        date=transaction_data.date,
        category_confidence=category_confidence,
        categorization_method=categorization_method,
    )
    db.add(transaction)
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

    if transaction_type in {"income", "expense"}:
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
    else:
        ensure_category_exists(db, new_category_id)
        transaction.category_confidence = 1.0
        transaction.categorization_method = "manual"
        learn_user_category_preference(
            db,
            current_user.id,
            transaction_data.merchant,
            new_category_id,
        )

    if old_category_id != new_category_id and new_category_id is not None:
        db.add(
            CategoryCorrection(
                user_id=current_user.id,
                transaction_id=transaction.id,
                old_category_id=old_category_id,
                new_category_id=new_category_id,
                merchant=transaction_data.merchant or transaction.merchant,
                original_description=transaction_data.description,
                correction_source="manual",
            )
        )

    transaction.amount = transaction_data.amount
    transaction.category_id = new_category_id
    transaction.description = transaction_data.description
    transaction.merchant = transaction_data.merchant
    transaction.transaction_type = transaction_data.transaction_type
    transaction.date = transaction_data.date

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
