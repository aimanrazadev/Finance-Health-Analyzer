import re
import unicodedata

from rapidfuzz import fuzz

from app.services.merchant_extractor_service import extract_transaction_merchant, normalize_description


TRAILING_NOISE_WORDS = {
    "MIN",
    "P2P",
    "PAY",
    "PAID",
    "PAYMENT",
    "FROM",
    "PH",
    "PHONE",
    "UPI",
    "VALUE",
    "DATE",
    "WHATSAPP",
    "REMARKS",
    "NO",
    "BY",
}


def _ascii_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    return text.encode("ascii", "ignore").decode("ascii")


def normalize_friend_key(value: str | None) -> str:
    """Stable duplicate-prevention key used for exact friend matching."""
    name = extract_friend_name(value)
    text = re.sub(r"[^A-Z ]", " ", name.upper())
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def compact_friend_key(value: str | None) -> str:
    """Compact key catches variants like 'ARYAN MALHOTRA' and 'aryanmalhotra'."""
    return re.sub(r"[^a-z0-9]", "", normalize_friend_key(value))


def display_friend_name(value: str | None) -> str:
    """Human-readable normalized friend name stored in the friends table."""
    key = normalize_friend_key(value)
    return key.upper()


def extract_friend_name(description: str | None) -> str:
    """Extract a meaningful person name from UPI/bank narration text."""
    text = _ascii_text(description)
    text = normalize_description(text)
    if not text:
        return ""

    parts = [part.strip() for part in re.split(r"[/|]", text) if part.strip()]
    candidate = ""

    if parts and parts[0].upper() in {"UPI", "IMPS", "NEFT", "RTGS", "MB", "PCI"} and len(parts) > 1:
        candidate = parts[1]
    elif parts:
        merchant = extract_transaction_merchant(text)
        candidate = merchant or parts[0]
    else:
        candidate = extract_transaction_merchant(text) or text

    candidate = re.sub(r"\+\d{8,}", " ", candidate.upper())
    candidate = re.sub(r"\b\d+\b", " ", candidate)
    candidate = re.sub(r"[^A-Z ]", " ", candidate)
    tokens = [token for token in candidate.split() if token and token not in TRAILING_NOISE_WORDS]

    while tokens and tokens[-1] in TRAILING_NOISE_WORDS:
        tokens.pop()

    # Bank narrations often include a third surname/noise token. Two tokens are
    # enough to create stable human friend groups for this project.
    if len(tokens) > 2:
        tokens = tokens[:2]

    return " ".join(tokens).strip()


def transaction_friend_candidate(transaction) -> str:
    """Pick the best text source for friend matching on one transaction."""
    return (
        extract_friend_name(transaction.extracted_merchant)
        or extract_friend_name(transaction.merchant)
        or extract_friend_name(transaction.description)
    )


def friend_names_match(friend_name: str | None, candidate: str | None, threshold: int = 90) -> bool:
    """Exact, compact, then fuzzy matching for friend/person names."""
    friend_key = normalize_friend_key(friend_name)
    candidate_key = normalize_friend_key(candidate)
    if not friend_key or not candidate_key:
        return False

    if friend_key == candidate_key:
        return True

    if compact_friend_key(friend_key) == compact_friend_key(candidate_key):
        return True

    return fuzz.token_set_ratio(friend_key, candidate_key) >= threshold
