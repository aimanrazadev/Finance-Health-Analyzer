from datetime import datetime
import math
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import Category
from app.services.categorization import categorize_transaction
from app.services.merchant_extractor_service import extract_merchant_name
from app.services.transaction_type_service import normalize_transaction_type

COLUMN_ALIASES = {
    "transaction_date": {"date", "transaction_date", "date_of_transaction", "txn_date", "value_date"},
    "description": {"description", "narration", "particulars", "details", "transaction", "memo"},
    "reference_no": {"chq/ref_no", "chq_ref_no", "ref_no", "reference", "reference_no", "chq/ref._no."},
    "withdrawal_amount": {"withdrawal", "withdrawal_dr", "withdrawal_(dr.)", "debit", "dr", "withdrawal_amount"},
    "deposit_amount": {"deposit", "deposit_cr", "deposit_(cr.)", "credit", "cr", "deposit_amount"},
    "balance": {"balance", "closing_balance", "available_balance"},
    "amount": {"amount", "value", "transaction_amount"},
    "transaction_type": {"type", "transaction_type", "debit_credit"},
    "merchant": {"merchant", "merchant_name", "payee", "vendor"},
}


def normalize_column_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = text.replace("-", "_")
    return text


def map_column_name(column_name: Any) -> str:
    normalized = normalize_column_name(column_name)
    compact = normalized.replace(".", "").replace("__", "_")
    for standard_name, aliases in COLUMN_ALIASES.items():
        if normalized in aliases or compact in aliases:
            return standard_name
    return normalized


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def parse_amount(value: Any) -> float | None:
    if is_blank(value):
        return None
    text = str(value).strip().replace(",", "")
    text = re.sub(r"(?i)\b(sar|inr|rs\.?|aed|usd)\b", "", text).strip()
    if text in {"-", ""}:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    return float(text)


def parse_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = datetime.strptime(str(value).strip(), "%d %b %Y")
    return parsed


def parse_date_flexible(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in (
        "%d %b %Y",
        "%d-%b-%Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"invalid date: {text}")


def detect_type_and_amount(withdrawal: float | None, deposit: float | None, amount: float | None, raw_type: Any = None) -> tuple[str, float]:
    raw_type_text = str(raw_type or "").strip().lower()
    if withdrawal and withdrawal > 0:
        return "expense", abs(withdrawal)
    if deposit and deposit > 0:
        return "income", abs(deposit)
    if raw_type_text in {"income", "credit", "cr", "deposit"} and amount is not None:
        return "income", abs(amount)
    if raw_type_text in {"expense", "debit", "dr", "withdrawal"} and amount is not None:
        return "expense", abs(amount)
    if amount is None:
        raise ValueError("amount is missing")
    return ("income", abs(amount)) if amount > 0 else ("expense", abs(amount))


def derive_merchant(description: str) -> str | None:
    return extract_merchant_name(description)


def standardize_transaction(
    raw: dict[str, Any],
    source: str,
    row_number: int,
    db: Session,
    user_id: int | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        description = str(raw.get("description") or "").strip()
        if not description:
            raise ValueError("description is missing")

        transaction_date = parse_date_flexible(raw.get("transaction_date"))
        withdrawal = parse_amount(raw.get("withdrawal_amount"))
        deposit = parse_amount(raw.get("deposit_amount"))
        balance = parse_amount(raw.get("balance"))
        amount = parse_amount(raw.get("amount"))
        transaction_type, final_amount = detect_type_and_amount(
            withdrawal,
            deposit,
            amount,
            raw.get("transaction_type"),
        )
        merchant = str(raw.get("merchant") or "").strip() or derive_merchant(description)
        reference_no = str(raw.get("reference_no") or "").strip() or None
        categorization = categorize_transaction(
            db,
            user_id,
            description,
            final_amount,
            transaction_type,
            merchant,
        )
        merchant = str(categorization.get("merchant") or merchant or "").strip() or None
        category_id = categorization.get("category_id")
        category = db.query(Category).filter(Category.id == category_id).first() if category_id else None
        transaction_type = normalize_transaction_type(db, transaction_type, category_id)

        return {
            "row_number": row_number,
            "transaction_date": transaction_date,
            "date": transaction_date,
            "description": description,
            "reference_no": reference_no,
            "withdrawal_amount": withdrawal,
            "deposit_amount": deposit,
            "balance": balance,
            "amount": final_amount,
            "transaction_type": transaction_type,
            "source": source,
            "merchant": merchant,
            "extracted_merchant": merchant,
            "category_id": category_id,
            "category": category.name if category else str(categorization.get("category_name") or "Other"),
            "category_name": category.name if category else str(categorization.get("category_name") or "Other"),
            "suggested_category_id": categorization.get("suggested_category_id"),
            "suggested_category_name": categorization.get("suggested_category_name"),
            "category_confidence": float(categorization.get("confidence") or 0.30),
            "categorization_method": str(categorization.get("method") or "needs_review"),
            "review_status": str(categorization.get("review_status") or "needs_review"),
            "is_needs_review": str(categorization.get("review_status") or "needs_review") == "needs_review",
            "requires_confirmation": bool(categorization.get("requires_confirmation")),
        }, None
    except Exception as exc:
        return None, {
            "row_number": row_number,
            "raw_data": raw,
            "error": str(exc),
        }
