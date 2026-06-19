import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.models import Friend, FriendMerchantLearning, Transaction
from app.services.merchant_extractor_service import normalize_description, normalize_merchant_name

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - fallback for minimal local installs
    fuzz = None

FRIEND_TRAILING_NOISE = {
    "BANK",
    "BHARATPE",
    "BY",
    "FROM",
    "GOOGLE",
    "INDIA",
    "LTD",
    "MIN",
    "PAY",
    "PAYMENT",
    "PHONEPE",
    "PVT",
    "REF",
    "REMARKS",
    "TO",
    "TRANSFER",
    "UPI",
    "VALUE",
    "WHATSAPP",
}


def normalize_friend_name(name: str | None) -> str:
    """Create one compact key so `Aryan Malhotra` and `aryanmalhotra` match."""
    text = normalize_description(name)
    text = re.sub(r"[^A-Za-z0-9]", "", text)
    text = text.strip().lower()
    return text


def extract_friend_name_from_text(description: str | None, merchant: str | None = None) -> str | None:
    """Extract a human friend name from UPI/bank narration text."""
    raw = normalize_description(merchant if merchant else description).upper()
    if not raw:
        return None

    parts = [part.strip(" :-") for part in re.split(r"[/|]", raw) if part.strip(" :-")]
    candidates: list[str] = []
    for part in parts:
        part = re.sub(r"\b\d{3,}\b", " ", part)
        part = re.sub(r"[^A-Z ]", " ", part)
        tokens = [
            token
            for token in re.sub(r"\s+", " ", part).strip().split()
            if token and token not in FRIEND_TRAILING_NOISE and not token.isdigit()
        ]
        if not tokens:
            continue
        if len(tokens) >= 2:
            candidates.append(" ".join(tokens[:2]))
        elif len(tokens[0]) >= 3:
            candidates.append(tokens[0])

    if not candidates and description and merchant:
        return extract_friend_name_from_text(description, None)

    if not candidates:
        return None

    return canonical_friend_display_name(candidates[0])


def canonical_friend_display_name(name: str | None) -> str | None:
    """Return the display name stored in Friends after removing noisy suffixes."""
    text = normalize_description(name).upper()
    text = re.sub(r"\b\d{3,}\b", " ", text)
    text = re.sub(r"[^A-Z ]", " ", text)
    tokens = [
        token
        for token in re.sub(r"\s+", " ", text).strip().split()
        if token and token not in FRIEND_TRAILING_NOISE
    ]
    if not tokens:
        return None
    return " ".join(tokens[:2]).title()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz:
        return fuzz.ratio(left, right) / 100
    return SequenceMatcher(None, left, right).ratio()


def _transaction_text(transaction: Transaction) -> str:
    friend_name = extract_friend_name_from_text(
        transaction.description,
        transaction.extracted_merchant or transaction.merchant,
    )
    parts = [friend_name, transaction.description, transaction.merchant, transaction.extracted_merchant]
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

    friend_candidate = extract_friend_name_from_text(
        transaction.description,
        transaction.extracted_merchant or transaction.merchant,
    )
    merchant_key = normalize_friend_name(friend_candidate) or normalize_merchant_name(
        transaction.extracted_merchant or transaction.merchant or transaction.description
    )
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
