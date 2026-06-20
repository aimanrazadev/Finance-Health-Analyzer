from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.models import FriendMerchantLearning
from app.services.friend_detection_service import display_friend_name, normalize_friend_key


def save_friend_learning_rule(db: Session, user_id: int, friend_id: int, merchant_name: str):
    """Create or refresh the learned merchant/person rule for a friend."""
    normalized = normalize_friend_key(merchant_name)
    if not normalized:
        return None

    for pending in db.new:
        if not isinstance(pending, FriendMerchantLearning):
            continue
        if pending.user_id == user_id and pending.normalized_merchant == normalized:
            pending.friend_id = friend_id
            pending.merchant_name = display_friend_name(merchant_name)
            pending.usage_count = (pending.usage_count or 0) + 1
            return pending

    rule = (
        db.query(FriendMerchantLearning)
        .filter(
            FriendMerchantLearning.user_id == user_id,
            FriendMerchantLearning.normalized_merchant == normalized,
        )
        .first()
    )
    if rule:
        rule.friend_id = friend_id
        rule.merchant_name = display_friend_name(merchant_name)
        rule.usage_count = (rule.usage_count or 0) + 1
        rule.last_used_at = func.now()
        return rule

    rule = FriendMerchantLearning(
        user_id=user_id,
        friend_id=friend_id,
        merchant_name=display_friend_name(merchant_name),
        normalized_merchant=normalized,
        confidence=0.95,
        usage_count=1,
        last_used_at=func.now(),
    )
    db.add(rule)
    return rule
