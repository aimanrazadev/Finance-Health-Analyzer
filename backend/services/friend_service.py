import re

from sqlalchemy.orm import Session

from models import Category, Debt, Friend, FriendTransactionLink, Transaction
from services.friend_learning_service import normalize_friend_text, save_friend_learning


def normalize_friend_name(name: str | None) -> str:
    """Normalize friend names for exact and fuzzy matching."""
    text = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def summarize_friend(db: Session, friend: Friend) -> dict:
    """Calculate all balance totals for one friend from debt ledger rows."""
    debts = db.query(Debt).filter(Debt.friend_id == friend.id, Debt.user_id == friend.user_id).all()
    transactions = (
        db.query(Transaction)
        .filter(Transaction.friend_id == friend.id, Transaction.user_id == friend.user_id)
        .order_by(Transaction.date.desc())
        .all()
    )
    total_lent = sum(debt.amount for debt in debts if debt.direction == "friend_owes_me")
    total_borrowed = sum(debt.amount for debt in debts if debt.direction == "i_owe_friend")
    total_friend_paid_back = sum(debt.amount for debt in debts if debt.direction == "reduces_friend_debt")
    total_i_paid_back = sum(debt.amount for debt in debts if debt.direction == "reduces_my_debt")
    money_friend_owes_me = max(total_lent - total_friend_paid_back, 0)
    money_i_owe_friend = max(total_borrowed - total_i_paid_back, 0)
    net_balance = round(money_friend_owes_me - money_i_owe_friend, 2)

    if net_balance == 0:
        status = "Paid / Settled"
    elif abs(net_balance) < max(total_lent, total_borrowed, 0):
        status = "Partially Paid"
    else:
        status = "Unpaid"

    return {
        "id": friend.id,
        "user_id": friend.user_id,
        "name": friend.name,
        "normalized_name": friend.normalized_name,
        "phone": friend.phone,
        "note": friend.note,
        "is_archived": friend.is_archived,
        "total_lent": round(total_lent, 2),
        "total_borrowed": round(total_borrowed, 2),
        "total_friend_paid_back": round(total_friend_paid_back, 2),
        "total_i_paid_back": round(total_i_paid_back, 2),
        "net_balance": net_balance,
        "status": status,
        "last_transaction_date": transactions[0].date if transactions else None,
        "created_at": friend.created_at,
    }


def get_friend_dashboard(db: Session, user_id: int, include_archived: bool = False, search: str | None = None) -> dict:
    """Build dashboard cards and friend summaries for the current user."""
    query = db.query(Friend).filter(Friend.user_id == user_id)
    if not include_archived:
        query = query.filter(Friend.is_archived == False)  # noqa: E712
    if search:
        query = query.filter(Friend.normalized_name.ilike(f"%{normalize_friend_name(search)}%"))
    friends = query.order_by(Friend.name).all()
    summaries = [summarize_friend(db, friend) for friend in friends]
    friends_owe_me = sum(item["net_balance"] for item in summaries if item["net_balance"] > 0)
    i_owe_friends = abs(sum(item["net_balance"] for item in summaries if item["net_balance"] < 0))
    return {
        "total_friends": len(summaries),
        "friends_owe_me": round(friends_owe_me, 2),
        "i_owe_friends": round(i_owe_friends, 2),
        "net_balance": round(friends_owe_me - i_owe_friends, 2),
        "settled_friends": sum(1 for item in summaries if item["net_balance"] == 0),
        "unsettled_friends": sum(1 for item in summaries if item["net_balance"] != 0),
        "friends": summaries,
    }


def _friends_category_id(db: Session) -> int | None:
    category = db.query(Category).filter(Category.name == "Friends").first()
    if category:
        return category.id
    category = Category(name="Friends", description="Friends and debt tracking")
    db.add(category)
    db.flush()
    return category.id


def auto_attach_matching_transactions(db: Session, user_id: int, friend: Friend) -> int:
    """Attach existing unlinked transactions whose narration clearly contains the friend's name."""
    category_id = _friends_category_id(db)
    normalized_friend = normalize_friend_name(friend.name)
    if not normalized_friend:
        return 0

    attached_count = 0
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.friend_id.is_(None),
        )
        .all()
    )
    for transaction in transactions:
        normalized_text = normalize_friend_text(f"{transaction.description} {transaction.merchant or ''}")
        if normalized_friend not in normalized_text:
            continue

        transaction.original_category_id = transaction.original_category_id or transaction.category_id
        transaction.category_id = category_id
        transaction.friend_id = friend.id
        transaction.is_friend_transaction = True
        transaction.is_needs_review = False
        transaction.review_reason = None
        transaction.debt_type = transaction.debt_type or "unclassified_friend"
        transaction.debt_direction = transaction.debt_direction or "no_debt"
        transaction.categorization_method = "friend_match"
        transaction.category_confidence = 0.95

        existing_link = (
            db.query(FriendTransactionLink)
            .filter(
                FriendTransactionLink.user_id == user_id,
                FriendTransactionLink.friend_id == friend.id,
                FriendTransactionLink.transaction_id == transaction.id,
            )
            .first()
        )
        if not existing_link:
            db.add(FriendTransactionLink(user_id=user_id, friend_id=friend.id, transaction_id=transaction.id))
        save_friend_learning(db, user_id, friend.id, transaction.description, 0.95)
        attached_count += 1

    return attached_count
