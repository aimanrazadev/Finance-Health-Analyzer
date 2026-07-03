from sqlalchemy.orm import Session

VALID_TRANSACTION_TYPES = {"income", "expense"}


def normalize_transaction_type(
    db: Session,
    transaction_type: str,
    category_id: int | None,
) -> str:
    """Keep the bank-derived direction independent from transaction category."""
    del db, category_id
    normalized = (transaction_type or "").strip().lower()
    return normalized if normalized in VALID_TRANSACTION_TYPES else "expense"
