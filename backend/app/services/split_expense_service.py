from sqlalchemy.orm import Session

from app.models.models import Transaction
from app.services.debt_service import create_debt, get_friends_category_id


def create_split_expense(
    db: Session,
    user_id: int,
    total_amount: float,
    shares: list,
    transaction: Transaction | None = None,
    description: str | None = None,
):
    """Create separate debt records for each friend in a split expense."""
    debts = []
    if transaction:
        transaction.category_id = get_friends_category_id(db)
        transaction.is_friend_transaction = True
        transaction.debt_type = "split_expense"
        transaction.debt_direction = "friend_owes_me"
        transaction.is_needs_review = False
    for share in shares:
        debts.append(
            create_debt(
                db,
                user_id,
                share.friend_id,
                share.amount,
                "split_expense",
                "friend_owes_me",
                transaction.id if transaction else None,
                share.note or description or f"Split expense from INR {total_amount:.2f}",
            )
        )
    return debts
