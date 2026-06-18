import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.models import Friend, FriendMerchantLearning, Transaction
from app.services.merchant_extractor_service import normalize_description, normalize_merchant_name

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - fallback for minimal local installs
    fuzz = None


def normalize_friend_name(name: str | None) -> str:
    """Create a stable lowercase key for friend-name matching."""
    text = normalize_description(name)
    text = re.sub(r"[^A-Za-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz:
        return fuzz.ratio(left, right) / 100
    return SequenceMatcher(None, left, right).ratio()


def _transaction_text(transaction: Transaction) -> str:
    parts = [
        transaction.description,
        transaction.merchant,
        transaction.extracted_merchant,
    ]
    return normalize_friend_name(" ".join(part for part in parts if part))


def detect_friend_for_transaction(
    db: Session,
    user_id: int,
    transaction: Transaction,
) -> dict[str, object] | None:
    """Return the best friend match for a transaction, if the text is confident."""
    text = _transaction_text(transaction)
    if not text:
        return None

    friends = (
        db.query(Friend)
        .filter(Friend.user_id == user_id, Friend.is_active == True)  # noqa: E712
        .all()
    )
    for friend in friends:
        normalized_name = friend.normalized_name or normalize_friend_name(friend.name)
        if normalized_name and normalized_name in text:
            return {
                "friend_id": friend.id,
                "friend_name": friend.name,
                "confidence": 0.95,
                "reason": "friend_name_match",
            }

    merchant_key = normalize_merchant_name(transaction.extracted_merchant or transaction.merchant or transaction.description)
    learned_rows = (
        db.query(FriendMerchantLearning)
        .filter(FriendMerchantLearning.user_id == user_id)
        .all()
    )
    best: tuple[FriendMerchantLearning, float] | None = None
    for row in learned_rows:
        score = _similarity(merchant_key, row.normalized_merchant)
        if score >= 0.78 and (best is None or score > best[1]):
            best = (row, score)

    if best:
        friend = db.query(Friend).filter(Friend.id == best[0].friend_id, Friend.user_id == user_id).first()
        if friend and friend.is_active:
            return {
                "friend_id": friend.id,
                "friend_name": friend.name,
                "confidence": min(0.95, best[1]),
                "reason": "learned_friend_pattern",
            }

    for friend in friends:
        normalized_name = friend.normalized_name or normalize_friend_name(friend.name)
        score = _similarity(text, normalized_name)
        if score >= 0.70:
            return {
                "friend_id": friend.id,
                "friend_name": friend.name,
                "confidence": score,
                "reason": "fuzzy_friend_match",
            }

    return None
