import re
import unicodedata


NOISE_TERMS = {
    "autope",
    "indian clearing",
    "payment from ph",
    "payment",
    "upi",
}

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
    text = re.sub(r"\b(UPI|MB|IMPS|NEFT|RTGS|FOS)[:/-]?", " ", text)
    text = re.sub(r"PAYMENT FROM PH(?:ONE)?", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" /:-")
    return text


def _candidate_from_received(description: str) -> str | None:
    match = re.search(r"RECEIVED FROM\s+([^/:-]+)", description, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_merchant_name(description: str | None) -> str | None:
    """Extract a stable merchant/person name from noisy bank transaction text."""
    normalized = normalize_description(description)
    if not normalized:
        return None

    received_candidate = _candidate_from_received(normalized)
    if received_candidate:
        return received_candidate.upper()

    parts = [part.strip(" :-").upper() for part in re.split(r"[/|]", normalized) if part.strip()]
    useful_parts: list[str] = []
    for part in parts:
        if re.fullmatch(r"\d+", part):
            continue
        if part.lower() in NOISE_TERMS:
            continue
        if part in {"UPI", "MB", "IMPS", "NEFT", "RTGS", "FOS"}:
            continue
        useful_parts.append(re.sub(r"\s+", " ", part))

    if useful_parts:
        return useful_parts[0][:150]

    cleaned = clean_upi_description(normalized)
    return cleaned[:150] if cleaned else None


def normalize_merchant_name(merchant: str | None) -> str:
    """Create a compact normalized key for exact/fuzzy learned-rule matching."""
    text = clean_upi_description(merchant)
    text = re.sub(r"[^A-Z0-9 ]", " ", text.upper())
    text = re.sub(r"\s+", " ", text).strip()
    for canonical, aliases in MERCHANT_ALIASES.items():
        if any(alias in text for alias in aliases):
            return canonical
    return text
