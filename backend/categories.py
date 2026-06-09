from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Category, CategoryCorrection, CategoryLearningRule, FriendTransactionLink, Transaction, User
from schemas import (
    CategorizationRequest,
    CategorizationResponse,
    CategoryCorrectionRequest,
    CategoryCorrectionResponse,
    CategoryCreate,
    CategoryLearningRuleResponse,
    CategoryResponse,
    CategoryRetrainResponse,
    TransactionResponse,
)
from auth import get_current_user
from services.categorization import categorize_transaction as smart_categorize_transaction
from services.friend_detection_service import detect_friend_for_transaction
from services.learning_service import save_category_correction
from services.merchant_extractor_service import extract_merchant_name
from services.ml_categorization_service import MIN_TRAINING_LABELS, retrain_after_correction, train_user_category_model

router = APIRouter(prefix="/categories", tags=["categories"])

VISIBLE_CATEGORY_ORDER = [
    "Debt Cleared",
    "Refunds",
    "Bills",
    "Subscriptions",
    "Education",
    "Entertainment",
    "Food",
    "Friends",
    "Laundry",
    "Healthcare",
    "Investments",
    "Salary",
    "Groceries",
    "Shopping",
    "Travel",
    "Other",
]


@router.get("/", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Fetch user-facing categories in the product's preferred order."""
    categories = db.query(Category).filter(Category.name.in_(VISIBLE_CATEGORY_ORDER)).all()
    category_by_name = {category.name: category for category in categories}
    return [category_by_name[name] for name in VISIBLE_CATEGORY_ORDER if name in category_by_name]


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new category"""
    existing = db.query(Category).filter(Category.name == category_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category_data.name}' already exists."
        )

    category = Category(
        name=category_data.name,
        description=category_data.description,
        color=category_data.color,
        icon=category_data.icon,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.post("/categorize", response_model=CategorizationResponse)
def categorize_transaction_preview(
    request: CategorizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Predict a category from a transaction description and optional merchant."""
    result = smart_categorize_transaction(
        db,
        current_user.id,
        request.description,
        merchant=request.merchant,
    )
    return CategorizationResponse(
        category_name=str(result["category_name"]),
        category_id=result["category_id"] if isinstance(result["category_id"], int) else None,
        suggested_category_id=result["suggested_category_id"] if isinstance(result.get("suggested_category_id"), int) else None,
        suggested_category_name=result.get("suggested_category_name"),
        confidence=float(result["confidence"]),
        method=str(result["method"]),
        merchant=result.get("merchant"),
        requires_confirmation=bool(result.get("requires_confirmation")),
    )


@router.post("/correct", response_model=CategoryCorrectionResponse)
def correct_transaction_category(
    request: CategoryCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a manual correction and save a user-specific learned merchant rule."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == request.transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    category = db.query(Category).filter(Category.id == request.new_category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected category does not exist")

    old_category_id = transaction.category_id
    correction = save_category_correction(
        db,
        current_user.id,
        transaction.id,
        old_category_id,
        request.new_category_id,
    )
    transaction.category_id = request.new_category_id
    transaction.category_confidence = 1.0
    transaction.categorization_method = "manual"
    transaction.merchant = transaction.merchant or correction.merchant
    transaction.is_needs_review = False

    if category.name == "Friends":
        transaction.is_friend_transaction = True
        transaction.debt_type = transaction.debt_type or "unclassified_friend"
        transaction.debt_direction = transaction.debt_direction or "no_debt"

        suggestion = detect_friend_for_transaction(db, current_user.id, transaction)
        if suggestion and suggestion.get("confidence", 0) >= 0.80:
            transaction.friend_id = suggestion["friend_id"]
            existing_link = (
                db.query(FriendTransactionLink)
                .filter(
                    FriendTransactionLink.user_id == current_user.id,
                    FriendTransactionLink.transaction_id == transaction.id,
                    FriendTransactionLink.friend_id == suggestion["friend_id"],
                )
                .first()
            )
            if not existing_link:
                db.add(FriendTransactionLink(
                    user_id=current_user.id,
                    friend_id=suggestion["friend_id"],
                    transaction_id=transaction.id,
                    debt_id=None,
                ))
    else:
        transaction.is_friend_transaction = False
        transaction.friend_id = None

    retrain_after_correction(current_user.id)
    db.commit()

    return CategoryCorrectionResponse(
        transaction_id=transaction.id,
        old_category_id=old_category_id,
        new_category_id=request.new_category_id,
        merchant_name=correction.merchant,
        message="Category updated. Learning rule saved. Similar future transactions will be categorized automatically.",
    )


@router.get("/needs-review", response_model=List[TransactionResponse])
def get_needs_review_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_learned: bool = False,
):
    """Return unclear transactions that need a user category correction."""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if include_learned:
        return query.order_by(Transaction.date.desc()).all()

    needs_review_category = db.query(Category).filter(Category.name == "Needs Review").first()
    filters = [
        Transaction.category_confidence.is_(None),
        Transaction.category_confidence < 0.80,
    ]
    if needs_review_category:
        filters.append(Transaction.category_id == needs_review_category.id)
    query = query.filter(
        or_(Transaction.is_friend_transaction == False, Transaction.is_friend_transaction.is_(None)),  # noqa: E712
        Transaction.friend_id.is_(None),
        or_(*filters),
    )
    return query.order_by(Transaction.date.desc()).all()


@router.post("/retrain", response_model=CategoryRetrainResponse)
def retrain_category_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrain the current user's ML categorization model when enough labels exist."""
    label_count = db.query(CategoryCorrection).filter(CategoryCorrection.user_id == current_user.id).count()
    retrain_after_correction(current_user.id)
    model = train_user_category_model(db, current_user.id)
    trained = model is not None
    return CategoryRetrainResponse(
        trained=trained,
        label_count=label_count,
        message=(
            "Model retrained."
            if trained
            else f"Need at least {MIN_TRAINING_LABELS} corrected transactions to train the ML model."
        ),
    )


@router.get("/learning-rules", response_model=List[CategoryLearningRuleResponse])
def get_learning_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return learned merchant rules for the current user only."""
    rows = (
        db.query(CategoryLearningRule, Category)
        .outerjoin(Category, CategoryLearningRule.category_id == Category.id)
        .filter(CategoryLearningRule.user_id == current_user.id)
        .order_by(CategoryLearningRule.times_used.desc(), CategoryLearningRule.updated_at.desc())
        .all()
    )
    return [
        CategoryLearningRuleResponse(
            id=rule.id,
            user_id=rule.user_id,
            merchant_pattern=rule.merchant_pattern,
            normalized_merchant=rule.normalized_merchant,
            category_id=rule.category_id,
            category_name=category.name if category else None,
            confidence_score=rule.confidence_score or 0.95,
            times_used=rule.times_used or 0,
            last_used_at=rule.last_used_at,
            created_at=rule.created_at,
        )
        for rule, category in rows
    ]
