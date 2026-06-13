import re

from sqlalchemy.orm import Session

from app.models.models import FriendMerchantLearning


def normalize_friend_text(text: str | None) -> str:
    """Normalize transaction text for friend-pattern learning."""
    normalized = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())
    normalized = re.sub(r"\b\d+\b", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def save_friend_learning(db: Session, user_id: int, friend_id: int, raw_text: str, confidence: float) -> FriendMerchantLearning:
    """Save a user-confirmed mapping from transaction narration to a friend."""
    normalized_text = normalize_friend_text(raw_text)
    existing = (
        db.query(FriendMerchantLearning)
        .filter(
            FriendMerchantLearning.user_id == user_id,
            FriendMerchantLearning.friend_id == friend_id,
            FriendMerchantLearning.normalized_text == normalized_text,
        )
        .first()
    )
    if existing:
        existing.confidence = max(existing.confidence or 0, confidence)
        return existing

    learning = FriendMerchantLearning(
        user_id=user_id,
        friend_id=friend_id,
        raw_transaction_text=raw_text,
        normalized_text=normalized_text,
        confidence=confidence,
    )
    db.add(learning)
    return learning
