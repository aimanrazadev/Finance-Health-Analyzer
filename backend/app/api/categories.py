from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import Category, CategoryCorrection, CategoryLearningRule, FriendTransactionLink, Transaction, User
from app.schemas.schemas import (
    CategorizationRequest,
    CategorizationResponse,
    BulkCategoryCorrectionRequest,
    BulkCategoryCorrectionResponse,
    CategoryCorrectionRequest,
    CategoryCorrectionResponse,
    CategoryCreate,
    CategoryLearningRuleResponse,
    CategoryLearningRuleUpdate,
    CategoryResponse,
    CategoryRetrainResponse,
    TransactionResponse,
)
from app.api.auth import get_current_user
from app.services.categorization import categorize_transaction as smart_categorize_transaction
from app.services.category_service import create_category as create_category_service
from app.services.category_service import get_visible_categories
from app.services.friend_detection_service import detect_friend_for_transaction
from app.services.learning_service import save_category_correction
from app.services.merchant_extractor_service import normalize_merchant_name
from app.services.merchant_extractor_service import extract_merchant_name
from app.services.ml_categorization_service import MIN_TRAINING_LABELS, retrain_after_correction, train_user_category_model

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("/", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Fetch user-facing categories in the product's preferred order."""
    return get_visible_categories(db)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new category"""
    try:
        return create_category_service(db, category_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


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
    transaction.extracted_merchant = correction.merchant
    transaction.review_status = "approved"
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


@router.post("/bulk-correct", response_model=BulkCategoryCorrectionResponse)
def bulk_correct_transaction_categories(
    request: BulkCategoryCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply several category corrections and learn merchant rules for each."""
    updated_count = 0
    for item in request.corrections:
        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == item.transaction_id, Transaction.user_id == current_user.id)
            .first()
        )
        category = db.query(Category).filter(Category.id == item.new_category_id).first()
        if not transaction or not category:
            continue

        correction = save_category_correction(
            db,
            current_user.id,
            transaction.id,
            transaction.category_id,
            item.new_category_id,
            correction_source="bulk",
        )
        transaction.category_id = item.new_category_id
        transaction.category_confidence = 1.0
        transaction.categorization_method = "manual"
        transaction.extracted_merchant = correction.merchant
        transaction.merchant = transaction.merchant or correction.merchant
        transaction.review_status = "approved"
        transaction.is_needs_review = False
        updated_count += 1

    retrain_after_correction(current_user.id)
    db.commit()
    return BulkCategoryCorrectionResponse(
        updated_count=updated_count,
        message=f"Saved {updated_count} category correction{'s' if updated_count != 1 else ''}.",
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
            merchant_name=rule.merchant_name or rule.merchant_pattern,
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


@router.put("/learning-rules/{rule_id}", response_model=CategoryLearningRuleResponse)
def update_learning_rule(
    rule_id: int,
    payload: CategoryLearningRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit a learned merchant mapping for the current user only."""
    rule = (
        db.query(CategoryLearningRule)
        .filter(CategoryLearningRule.id == rule_id, CategoryLearningRule.user_id == current_user.id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning rule not found")

    if payload.category_id is not None:
        category = db.query(Category).filter(Category.id == payload.category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected category does not exist")
        rule.category_id = payload.category_id

    if payload.merchant_name is not None:
        normalized = normalize_merchant_name(payload.merchant_name)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Merchant name is required")
        rule.merchant_pattern = payload.merchant_name
        rule.merchant_name = payload.merchant_name
        rule.normalized_merchant = normalized

    db.commit()
    db.refresh(rule)
    category = db.query(Category).filter(Category.id == rule.category_id).first()
    return CategoryLearningRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        merchant_pattern=rule.merchant_pattern,
        merchant_name=rule.merchant_name or rule.merchant_pattern,
        normalized_merchant=rule.normalized_merchant,
        category_id=rule.category_id,
        category_name=category.name if category else None,
        confidence_score=rule.confidence_score or rule.confidence or 1.0,
        times_used=rule.times_used or rule.usage_count or 0,
        last_used_at=rule.last_used_at,
        created_at=rule.created_at,
    )


@router.delete("/learning-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_learning_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a learned merchant mapping for the current user only."""
    rule = (
        db.query(CategoryLearningRule)
        .filter(CategoryLearningRule.id == rule_id, CategoryLearningRule.user_id == current_user.id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning rule not found")
    db.delete(rule)
    db.commit()
