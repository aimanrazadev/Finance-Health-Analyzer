from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.models import Category, CategoryCorrection, CategoryLearningRule, Transaction, User
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
    LearningAccuracyResponse,
    CategoryResponse,
    CategoryRetrainResponse,
    TransactionResponse,
)
from app.api.deps import get_current_user
from app.services.categorization_service import categorize_transaction as smart_categorize_transaction
from app.services.category_service import create_category as create_category_service
from app.services.category_service import get_visible_categories
from app.services.friend_service import (
    create_or_update_friend_from_transaction,
    detach_transaction_from_friend,
    is_friends_category,
)
from app.services.learning_service import save_category_correction
from app.utils.merchant_extractor import normalize_merchant_name
from app.ml.categorization import (
    MIN_TRAINING_LABELS,
    evaluate_user_category_model,
    evaluate_user_learning_accuracy,
    retrain_after_correction,
    train_user_category_model,
)
from app.utils.transaction_type import normalize_transaction_type

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Fetch user-facing categories in the product's preferred order."""
    return get_visible_categories(db)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
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

    if not db.query(Category).filter(Category.id == request.new_category_id).first():
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
    transaction.transaction_type = normalize_transaction_type(
        db,
        transaction.transaction_type,
        request.new_category_id,
    )
    transaction.category_confidence = 1.0
    transaction.categorization_method = "manual"
    transaction.suggested_category_id = None
    transaction.suggested_category_name = None
    transaction.extracted_merchant = correction.merchant
    transaction.review_status = "approved"
    transaction.merchant = transaction.merchant or correction.merchant
    transaction.is_needs_review = False

    if is_friends_category(db, request.new_category_id):
        try:
            friend, _ = create_or_update_friend_from_transaction(db, current_user.id, transaction)
            transaction.friend_id = friend.id
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        detach_transaction_from_friend(db, current_user.id, transaction)

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
    transaction_ids = {item.transaction_id for item in request.corrections}
    if len(transaction_ids) != len(request.corrections):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Each transaction may appear only once in a bulk correction",
        )
    category_ids = {item.new_category_id for item in request.corrections}
    transactions = {
        row.id: row for row in db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.id.in_(transaction_ids),
        ).all()
    }
    categories = {row.id for row in db.query(Category).filter(Category.id.in_(category_ids)).all()}
    if len(transactions) != len(transaction_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more transactions were not found")
    if categories != category_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more selected categories do not exist")

    updated_count = 0
    for item in request.corrections:
        transaction = transactions[item.transaction_id]

        correction = save_category_correction(
            db,
            current_user.id,
            transaction.id,
            transaction.category_id,
            item.new_category_id,
            correction_source="bulk",
        )
        transaction.category_id = item.new_category_id
        transaction.transaction_type = normalize_transaction_type(
            db,
            transaction.transaction_type,
            item.new_category_id,
        )
        transaction.category_confidence = 1.0
        transaction.categorization_method = "manual"
        transaction.suggested_category_id = None
        transaction.suggested_category_name = None
        transaction.extracted_merchant = correction.merchant
        transaction.merchant = transaction.merchant or correction.merchant
        transaction.review_status = "approved"
        transaction.is_needs_review = False
        if is_friends_category(db, item.new_category_id):
            try:
                create_or_update_friend_from_transaction(db, current_user.id, transaction)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        else:
            detach_transaction_from_friend(db, current_user.id, transaction)
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
    include_approved: bool = False,
    include_learned: bool | None = None,
):
    """Return unclear transactions that need a user category correction."""
    query = (
        db.query(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == current_user.id)
    )
    if include_approved or include_learned is True:
        rows = query.order_by(Transaction.date.desc()).all()
        return [
            {**transaction.__dict__, "category_name": category.name if category else None}
            for transaction, category in rows
        ]

    filters = [
        Transaction.category_confidence.is_(None),
        Transaction.category_confidence < 0.80,
        Transaction.review_status == "needs_review",
        Transaction.is_needs_review == True,  # noqa: E712
        Transaction.categorization_method == "needs_review",
        Transaction.category_id.is_(None),
    ]
    query = query.filter(
        or_(Transaction.is_friend_transaction == False, Transaction.is_friend_transaction.is_(None)),  # noqa: E712
        or_(*filters),
    )
    rows = query.order_by(Transaction.date.desc()).all()
    return [
        {**transaction.__dict__, "category_name": category.name if category else None}
        for transaction, category in rows
    ]


@router.get("/learning-accuracy", response_model=LearningAccuracyResponse)
def get_learning_accuracy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return held-out accuracy based only on the user's manual corrections."""
    evaluation = evaluate_user_learning_accuracy(db, current_user.id)
    return LearningAccuracyResponse(**evaluation)


@router.post("/retrain", response_model=CategoryRetrainResponse)
def retrain_category_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrain the current user's ML categorization model when enough labels exist."""
    label_count = db.query(CategoryCorrection).filter(CategoryCorrection.user_id == current_user.id).count()
    retrain_after_correction(current_user.id)
    model = train_user_category_model(db, current_user.id)
    evaluation = evaluate_user_category_model(db, current_user.id)
    trained = model is not None
    return CategoryRetrainResponse(
        trained=trained,
        label_count=label_count,
        message=(
            f"Model retrained. {evaluation['message']}"
            if trained
            else f"Need at least {MIN_TRAINING_LABELS} corrected transactions to train the ML model."
        ),
        accuracy=evaluation.get("accuracy"),
        class_count=int(evaluation.get("class_count") or 0),
        test_sample_count=int(evaluation.get("test_sample_count") or 0),
        evaluation_type=str(evaluation.get("evaluation_type") or "not_evaluated"),
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
