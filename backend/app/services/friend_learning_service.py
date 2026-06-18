from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import FriendMerchantLearning
from app.services.merchant_extractor_service import normalize_merchant_name


def save_friend_learning_rule(
    db: Session,
    user_id: int,
    friend_id: int,
    merchant_pattern: str | None,
) -> FriendMerchantLearning | None:
    """Remember transaction text that repeatedly belongs to a friend."""
    normalized = normalize_merchant_name(merchant_pattern)
    if not normalized:
        return None

    rule = (
        db.query(FriendMerchantLearning)
        .filter(
            FriendMerchantLearning.user_id == user_id,
            FriendMerchantLearning.friend_id == friend_id,
            FriendMerchantLearning.normalized_merchant == normalized,
        )
        .first()
    )
    if rule:
        rule.usage_count = (rule.usage_count or 0) + 1
        rule.last_used_at = datetime.utcnow()
        return rule

    rule = FriendMerchantLearning(
        user_id=user_id,
        friend_id=friend_id,
        merchant_pattern=merchant_pattern or normalized,
        normalized_merchant=normalized,
        confidence=0.95,
        usage_count=1,
        last_used_at=datetime.utcnow(),
    )
    db.add(rule)
    return rule
