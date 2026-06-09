from sqlalchemy.orm import Session

from models import Category, Debt, Friend, FriendTransactionLink, Transaction
from services.friend_learning_service import save_friend_learning
from services.friend_service import summarize_friend


VALID_DIRECTIONS = {
    "friend_owes_me",
    "i_owe_friend",
    "reduces_friend_debt",
    "reduces_my_debt",
    "no_debt",
}


def get_friends_category_id(db: Session) -> int | None:
    """Return the Friends category id, creating it if needed."""
    category = db.query(Category).filter(Category.name == "Friends").first()
    if category:
        return category.id
    category = Category(name="Friends", description="Friends and debt tracking")
    db.add(category)
    db.flush()
    return category.id


def suggest_direction_for_transaction(db: Session, friend_id: int, transaction: Transaction) -> tuple[str, str]:
    """Suggest debt meaning from transaction type and current balance."""
    friend = db.query(Friend).filter(Friend.id == friend_id, Friend.user_id == transaction.user_id).first()
    summary = summarize_friend(db, friend)
    if transaction.transaction_type == "expense":
        if summary["net_balance"] < 0:
            return "my_repayment", "reduces_my_debt"
        return "lent", "friend_owes_me"
    if summary["net_balance"] > 0:
        return "friend_repayment", "reduces_friend_debt"
    return "borrowed", "i_owe_friend"


def create_debt(
    db: Session,
    user_id: int,
    friend_id: int,
    amount: float,
    debt_type: str,
    direction: str,
    transaction_id: int | None = None,
    note: str | None = None,
) -> Debt:
    """Create one debt ledger entry; gifts/no-debt stay auditable but do not affect balance."""
    debt = Debt(
        user_id=user_id,
        friend_id=friend_id,
        transaction_id=transaction_id,
        amount=amount,
        debt_type=debt_type,
        direction=direction,
        status="paid" if direction == "no_debt" else "unpaid",
        note=note,
    )
    db.add(debt)
    db.flush()
    return debt


def link_transaction_to_friend(
    db: Session,
    user_id: int,
    transaction: Transaction,
    friend_id: int,
    debt_type: str,
    direction: str,
    amount: float | None = None,
    note: str | None = None,
) -> Debt:
    """Link a transaction to a friend, set category Friends, and create a debt record."""
    if transaction.friend_id and transaction.friend_id != friend_id:
        raise ValueError("Transaction is already linked to another friend")
    if direction not in VALID_DIRECTIONS:
        raise ValueError("Invalid debt direction")

    transaction.original_category_id = transaction.original_category_id or transaction.category_id
    transaction.category_id = get_friends_category_id(db)
    transaction.friend_id = friend_id
    transaction.debt_type = debt_type
    transaction.debt_direction = direction
    transaction.is_friend_transaction = True
    transaction.is_needs_review = False
    transaction.review_reason = None
    transaction.category_confidence = 1.0
    transaction.categorization_method = "manual"

    debt = create_debt(
        db,
        user_id,
        friend_id,
        amount or transaction.amount,
        debt_type,
        direction,
        transaction.id,
        note,
    )
    db.add(FriendTransactionLink(user_id=user_id, friend_id=friend_id, transaction_id=transaction.id, debt_id=debt.id))
    save_friend_learning(db, user_id, friend_id, transaction.description, 0.95)
    return debt


def unlink_transaction_from_friend(db: Session, user_id: int, transaction: Transaction) -> None:
    """Remove friend link and related debt records while keeping the transaction safe."""
    db.query(Debt).filter(Debt.user_id == user_id, Debt.transaction_id == transaction.id).delete(synchronize_session=False)
    db.query(FriendTransactionLink).filter(
        FriendTransactionLink.user_id == user_id,
        FriendTransactionLink.transaction_id == transaction.id,
    ).delete(synchronize_session=False)
    transaction.friend_id = None
    transaction.debt_type = None
    transaction.debt_direction = None
    transaction.is_friend_transaction = False
    transaction.category_id = transaction.original_category_id
    transaction.is_needs_review = True
    transaction.review_reason = "Friend link removed"
