from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Category


SAVINGS_CATEGORY_NAMES = {"investment", "investments", "mutual fund", "mutual funds", "sip", "stocks"}
VALID_TRANSACTION_TYPES = {"income", "expense", "savings"}


def is_savings_category(category: Optional[Category]) -> bool:
    """Return true when a category should be treated as a savings movement."""
    return bool(category and category.name and category.name.strip().lower() in SAVINGS_CATEGORY_NAMES)


def normalize_transaction_type(
    db: Session,
    transaction_type: str,
    category_id: Optional[int],
) -> str:
    """Force investment-category transactions into the savings transaction type."""
    category = db.query(Category).filter(Category.id == category_id).first() if category_id else None
    if is_savings_category(category):
        return "savings"
    normalized = (transaction_type or "").strip().lower()
    return normalized if normalized in VALID_TRANSACTION_TYPES else "expense"
