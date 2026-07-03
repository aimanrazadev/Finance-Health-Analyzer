from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import CategoryCorrection, CategoryLearningRule, Transaction
from app.services.merchant_extractor_service import extract_merchant_name, normalize_merchant_name


def increment_rule_usage(db: Session, rule: CategoryLearningRule) -> None:
    """Track learned-rule usage so the user can see what the app reused."""
    rule.times_used = (rule.times_used or 0) + 1
    rule.usage_count = (rule.usage_count or 0) + 1
    rule.last_used_at = datetime.utcnow()


def create_or_update_learning_rule(
    db: Session,
    user_id: int,
    merchant_pattern: str | None,
    category_id: int,
) -> CategoryLearningRule | None:
    """Persist a user-specific merchant/category rule from a correction."""
    normalized_merchant = normalize_merchant_name(merchant_pattern)
    if not normalized_merchant:
        return None

    rule = (
        db.query(CategoryLearningRule)
        .filter(
            CategoryLearningRule.user_id == user_id,
            CategoryLearningRule.normalized_merchant == normalized_merchant,
        )
        .first()
    )
    if rule:
        rule.category_id = category_id
        rule.merchant_name = merchant_pattern or normalized_merchant
        rule.confidence_score = 1.0
        rule.confidence = 1.0
        rule.times_used = (rule.times_used or 0) + 1
        rule.usage_count = (rule.usage_count or 0) + 1
        rule.last_used_at = datetime.utcnow()
        return rule

    rule = CategoryLearningRule(
        user_id=user_id,
        merchant_pattern=merchant_pattern or normalized_merchant,
        merchant_name=merchant_pattern or normalized_merchant,
        normalized_merchant=normalized_merchant,
        category_id=category_id,
        confidence_score=1.0,
        confidence=1.0,
        times_used=1,
        usage_count=1,
        last_used_at=datetime.utcnow(),
    )
    db.add(rule)
    return rule


def save_category_correction(
    db: Session,
    user_id: int,
    transaction_id: int,
    old_category_id: int | None,
    new_category_id: int,
    correction_source: str = "manual",
) -> CategoryCorrection:
    """Store a correction and create/update the matching merchant learning rule."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user_id)
        .first()
    )
    if not transaction:
        raise ValueError("Transaction not found")

    merchant_name = transaction.merchant or extract_merchant_name(transaction.description)
    correction = CategoryCorrection(
        user_id=user_id,
        transaction_id=transaction_id,
        old_category_id=old_category_id,
        new_category_id=new_category_id,
        merchant=merchant_name,
        extracted_merchant=merchant_name,
        original_description=transaction.description,
        description=transaction.description,
        old_confidence=transaction.category_confidence,
        old_method=transaction.categorization_method,
        correction_source=correction_source,
    )
    db.add(correction)
    create_or_update_learning_rule(db, user_id, merchant_name, new_category_id)
    return correction
