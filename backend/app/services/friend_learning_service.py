from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import FriendMerchantLearning
from app.services.friend_detection_service import extract_friend_name_from_text, normalize_friend_name
from app.services.merchant_extractor_service import normalize_merchant_name


def save_friend_learning_rule(
    db: Session,
    user_id: int,
    friend_id: int,
    merchant_pattern: str | None,
) -> FriendMerchantLearning | None:
    """Remember transaction text that repeatedly belongs to a friend."""
    friend_name = extract_friend_name_from_text(merchant_pattern)
    normalized = normalize_friend_name(friend_name) or normalize_merchant_name(merchant_pattern)
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
        merchant_pattern=friend_name or merchant_pattern or normalized,
        normalized_merchant=normalized,
        confidence=0.95,
        usage_count=1,
        last_used_at=datetime.utcnow(),
    )
    db.add(rule)
    return rule
