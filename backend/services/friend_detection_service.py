from sqlalchemy.orm import Session

from models import Friend, FriendMerchantLearning, Transaction
from services.friend_learning_service import normalize_friend_text
from services.friend_service import normalize_friend_name

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None
    from difflib import SequenceMatcher


def _ratio(left: str, right: str) -> float:
    if fuzz:
        return fuzz.partial_ratio(left, right) / 100
    return SequenceMatcher(None, left, right).ratio()


def detect_friend_for_transaction(db: Session, user_id: int, transaction: Transaction) -> dict | None:
    """Suggest a friend for a transaction using learned mappings, exact names, then fuzzy names."""
    normalized_text = normalize_friend_text(f"{transaction.description} {transaction.merchant or ''}")

    learned_rows = db.query(FriendMerchantLearning).filter(FriendMerchantLearning.user_id == user_id).all()
    best_learned = None
    best_learning_score = 0.0
    for row in learned_rows:
        score = _ratio(normalized_text, row.normalized_text)
        if score > best_learning_score:
            best_learning_score = score
            best_learned = row
    if best_learned and best_learning_score >= 0.82:
        friend = db.query(Friend).filter(Friend.id == best_learned.friend_id, Friend.user_id == user_id).first()
        if friend:
            return {
                "transaction_id": transaction.id,
                "description": transaction.description,
                "amount": transaction.amount,
                "transaction_type": transaction.transaction_type,
                "friend_id": friend.id,
                "friend_name": friend.name,
                "confidence": round(max(best_learning_score, best_learned.confidence or 0), 2),
                "reason": "learned_friend_pattern",
            }

    friends = db.query(Friend).filter(Friend.user_id == user_id, Friend.is_archived == False).all()  # noqa: E712
    best_friend = None
    best_score = 0.0
    for friend in friends:
        exact_name = normalize_friend_name(friend.name)
        score = 1.0 if exact_name and exact_name in normalized_text else _ratio(normalized_text, exact_name)
        if score > best_score:
            best_score = score
            best_friend = friend

    if best_friend and best_score >= 0.70:
        return {
            "transaction_id": transaction.id,
            "description": transaction.description,
            "amount": transaction.amount,
            "transaction_type": transaction.transaction_type,
            "friend_id": best_friend.id,
            "friend_name": best_friend.name,
            "confidence": round(best_score, 2),
            "reason": "friend_name_match",
        }
    return None
