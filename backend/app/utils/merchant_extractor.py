import re
import unicodedata


NOISE_TERMS = {
    "autope",
    "indian clearing",
    "payment from ph",
    "payment",
    "pay",
    "ref",
    "txn",
    "transfer",
    "upi",
}

PAYMENT_RAILS = {"UPI", "PCI", "POS", "ATM", "MB", "IMPS", "NEFT", "RTGS", "FOS", "ACH", "NACH"}
CARD_DESCRIPTOR_TERMS = {"SUBSCR", "SUBSCRIPTION", "CHATGPT", "PAYMENT", "PURCHASE", "DEBIT", "CREDIT"}

MERCHANT_ALIASES = {
    "amazon": ("AMAZON", "AMZN", "AMZN MKTP", "AMAZON PAY", "AMAZON MARKETPLACE"),
    "flipkart": ("FLIPKART", "FKRT"),
    "swiggy": ("SWIGGY",),
    "zomato": ("ZOMATO",),
    "netflix": ("NETFLIX",),
    "uber": ("UBER",),
    "ola": ("OLA",),
}


def normalize_description(description: str | None) -> str:
    """Normalize bank narration text for matching and ML features."""
    text = unicodedata.normalize("NFKD", description or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9\s:/.-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_upi_description(description: str | None) -> str:
    """Remove common UPI/reference clutter while preserving useful merchant tokens."""
    text = normalize_description(description).upper()
    text = re.sub(r"\b\d{4,}\b", " ", text)
    text = re.sub(r"\b(UPI|PCI|POS|ATM|MB|IMPS|NEFT|RTGS|FOS|ACH|NACH)[:/-]?", " ", text)
    text = re.sub(r"PAYMENT FROM PH(?:ONE)?", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" /:-")
    return text


def _candidate_from_received(description: str) -> str | None:
    match = re.search(r"RECEIVED FROM\s+([^/:-]+)", description, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _clean_candidate(part: str) -> str | None:
    """Turn one bank narration segment into a displayable merchant candidate."""
    candidate = re.sub(r"\+\d{8,}", " ", part.upper())
    candidate = re.sub(r"\b\d{1,2}:\d{2}\b", " ", candidate)
    candidate = re.sub(r"\b\d{4,}\b", " ", candidate)
    candidate = re.sub(r"[^A-Z0-9 ]", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if not candidate:
        return None
    if candidate in PAYMENT_RAILS or candidate.lower() in NOISE_TERMS:
        return None

    words = candidate.split()
    if any(word in CARD_DESCRIPTOR_TERMS for word in words[1:]):
        words = [words[0]]

    cleaned = " ".join(word for word in words if word not in CARD_DESCRIPTOR_TERMS).strip()
    return cleaned.title() if cleaned else None


def extract_merchant_name(description: str | None) -> str | None:
    """Extract a stable merchant/person name from noisy bank transaction text."""
    normalized = normalize_description(description)
    if not normalized:
        return None

    received_candidate = _candidate_from_received(normalized)
    if received_candidate:
        return received_candidate.title()

    parts = [part.strip(" :-").upper() for part in re.split(r"[/|]", normalized) if part.strip()]
    useful_parts: list[str] = []
    for part in parts:
        if re.fullmatch(r"\d+", part):
            continue
        if part.lower() in NOISE_TERMS:
            continue
        if part in PAYMENT_RAILS:
            continue
        candidate = _clean_candidate(part)
        if candidate:
            useful_parts.append(candidate)

    if useful_parts:
        return useful_parts[0][:150]

    cleaned = clean_upi_description(normalized)
    return cleaned[:150] if cleaned else None


def is_noisy_payment_merchant(merchant: str | None) -> bool:
    """Detect saved merchant values that are really payment rails or references."""
    text = normalize_description(merchant).upper().strip(" /:-")
    if not text:
        return True
    first_part = re.split(r"[/|:\- ]", text, maxsplit=1)[0]
    if text in PAYMENT_RAILS or first_part in PAYMENT_RAILS:
        return True
    if re.fullmatch(r"\d+", text):
        return True
    return False


def extract_transaction_merchant(description: str | None, merchant: str | None = None) -> str | None:
    """Prefer a real saved merchant, otherwise extract it from the bank narration."""
    if merchant and not is_noisy_payment_merchant(merchant):
        return extract_merchant_name(merchant) or merchant.strip()[:150]
    return extract_merchant_name(description) or extract_merchant_name(merchant)


def normalize_merchant_name(merchant: str | None) -> str:
    """Create a compact normalized key for exact/fuzzy learned-rule matching."""
    extracted = extract_merchant_name(merchant) if merchant and re.search(r"[/|]", merchant) else merchant
    text = clean_upi_description(extracted)
    text = re.sub(r"[^A-Z0-9 ]", " ", text.upper())
    text = re.sub(r"\s+", " ", text).strip()
    for canonical, aliases in MERCHANT_ALIASES.items():
        if any(alias in text for alias in aliases):
            return canonical
    return text.lower()
