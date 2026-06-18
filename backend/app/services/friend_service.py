from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.models import Category, Friend, FriendTransactionLink, Transaction
from app.services.friend_detection_service import detect_friend_for_transaction, normalize_friend_name
from app.services.friend_learning_service import save_friend_learning_rule
from app.services.merchant_extractor_service import extract_transaction_merchant


def get_friends_category_id(db: Session) -> int | None:
    category = db.query(Category).filter(Category.name == "Friends").first()
    return category.id if category else None


def create_friend(
    db: Session,
    user_id: int,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
) -> Friend:
    normalized_name = normalize_friend_name(name)
    if not normalized_name:
        raise ValueError("Friend name is required")

    friend = (
        db.query(Friend)
        .filter(
            Friend.user_id == user_id,
            Friend.normalized_name == normalized_name,
        )
        .order_by(Friend.id.desc())
        .first()
    )
    if friend:
        friend.name = name.strip()
        friend.email = email if email is not None else friend.email
        friend.phone = phone if phone is not None else friend.phone
        friend.notes = notes if notes is not None else friend.notes
        friend.is_active = True
        auto_attach_matching_transactions(db, user_id, friend)
        return friend

    friend = Friend(
        user_id=user_id,
        name=name.strip(),
        normalized_name=normalized_name,
        email=email,
        phone=phone,
        notes=notes,
        is_active=True,
    )
    db.add(friend)
    db.flush()
    auto_attach_matching_transactions(db, user_id, friend)
    return friend


def _link_exists(db: Session, friend_id: int, transaction_id: int) -> bool:
    return (
        db.query(FriendTransactionLink)
        .filter(
            FriendTransactionLink.friend_id == friend_id,
            FriendTransactionLink.transaction_id == transaction_id,
        )
        .first()
        is not None
    )


def attach_transaction_to_friend(
    db: Session,
    user_id: int,
    friend: Friend,
    transaction: Transaction,
) -> bool:
    """Attach one transaction to a friend and remove it from category review."""
    friends_category_id = get_friends_category_id(db)
    if friends_category_id is None:
        return False

    changed = transaction.friend_id != friend.id or not transaction.is_friend_transaction
    transaction.friend_id = friend.id
    transaction.is_friend_transaction = True
    transaction.category_id = friends_category_id
    transaction.category_confidence = 0.95
    transaction.categorization_method = "friend_match"
    transaction.review_status = "approved"
    transaction.is_needs_review = False

    if not _link_exists(db, friend.id, transaction.id):
        db.add(
            FriendTransactionLink(
                user_id=user_id,
                friend_id=friend.id,
                transaction_id=transaction.id,
                amount=transaction.amount,
                transaction_type=transaction.transaction_type,
            )
        )
        changed = True

    save_friend_learning_rule(
        db,
        user_id,
        friend.id,
        transaction.extracted_merchant or transaction.merchant or transaction.description,
    )
    return changed


def auto_attach_matching_transactions(db: Session, user_id: int, friend: Friend) -> int:
    """Attach all existing transactions that mention the saved friend's name."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc())
        .all()
    )
    attached_count = 0
    for transaction in transactions:
        suggestion = detect_friend_for_transaction(db, user_id, transaction)
        if suggestion and suggestion["friend_id"] == friend.id:
            if attach_transaction_to_friend(db, user_id, friend, transaction):
                attached_count += 1
    return attached_count


def auto_attach_transaction_if_friend(db: Session, user_id: int, transaction: Transaction) -> bool:
    """Attach a newly created/imported transaction if it matches any saved friend."""
    suggestion = detect_friend_for_transaction(db, user_id, transaction)
    if not suggestion:
        return False
    friend = (
        db.query(Friend)
        .filter(
            Friend.id == suggestion["friend_id"],
            Friend.user_id == user_id,
            Friend.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not friend:
        return False
    return attach_transaction_to_friend(db, user_id, friend, transaction)


def sync_friends_category_transactions(db: Session) -> int:
    """Repair rows categorized as Friends but not yet visible in the Friends module."""
    friends_category_id = get_friends_category_id(db)
    if friends_category_id is None:
        return 0

    linked_friend_ids = [
        row[0]
        for row in (
            db.query(Transaction.friend_id)
            .filter(Transaction.category_id == friends_category_id, Transaction.friend_id.isnot(None))
            .distinct()
            .all()
        )
    ]
    reactivated = 0
    if linked_friend_ids:
        linked_friends = (
            db.query(Friend)
            .filter(
                Friend.id.in_(linked_friend_ids),
                or_(Friend.is_active.is_(None), Friend.is_active == False),  # noqa: E712
            )
            .all()
        )
        for friend in linked_friends:
            friend.is_active = True
            reactivated += 1

    rows = (
        db.query(Transaction)
        .filter(
            Transaction.category_id == friends_category_id,
            (Transaction.friend_id.is_(None)) | (Transaction.is_friend_transaction == False),  # noqa: E712
        )
        .all()
    )
    repaired_count = 0
    for transaction in rows:
        friend_name = extract_transaction_merchant(
            transaction.description,
            transaction.extracted_merchant or transaction.merchant,
        )
        if not friend_name:
            continue

        normalized_name = normalize_friend_name(friend_name)
        if not normalized_name:
            continue

        friend = (
            db.query(Friend)
            .filter(
                Friend.user_id == transaction.user_id,
                Friend.normalized_name == normalized_name,
                Friend.is_active == True,  # noqa: E712
            )
            .first()
        )
        if not friend:
            friend = Friend(
                user_id=transaction.user_id,
                name=friend_name,
                normalized_name=normalized_name,
                is_active=True,
            )
            db.add(friend)
            db.flush()

        if attach_transaction_to_friend(db, transaction.user_id, friend, transaction):
            repaired_count += 1

    if repaired_count or reactivated:
        db.commit()
    return repaired_count + int(reactivated or 0)


def friend_summary(db: Session, user_id: int, friend_id: int) -> dict[str, float | int]:
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.friend_id == friend_id,
            Transaction.is_friend_transaction == True,  # noqa: E712
        )
        .all()
    )
    total_income = sum(row.amount for row in rows if row.transaction_type == "income")
    total_expense = sum(row.amount for row in rows if row.transaction_type == "expense")
    return {
        "transaction_count": len(rows),
        "total_income": total_income,
        "total_expense": total_expense,
        "net_amount": total_income - total_expense,
    }


def get_friend_dashboard(db: Session, user_id: int) -> dict[str, float | int]:
    active_count = (
        db.query(func.count(Friend.id))
        .filter(Friend.user_id == user_id, or_(Friend.is_active == True, Friend.is_active.is_(None)))  # noqa: E712
        .scalar()
        or 0
    )
    linked_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.user_id == user_id, Transaction.is_friend_transaction == True)  # noqa: E712
        .scalar()
        or 0
    )
    total_amount = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.user_id == user_id, Transaction.is_friend_transaction == True)  # noqa: E712
        .scalar()
        or 0
    )
    return {
        "active_friends": active_count,
        "linked_transactions": linked_count,
        "total_friend_amount": float(total_amount),
    }


__all__ = [
    "attach_transaction_to_friend",
    "auto_attach_matching_transactions",
    "auto_attach_transaction_if_friend",
    "create_friend",
    "friend_summary",
    "get_friend_dashboard",
    "normalize_friend_name",
    "sync_friends_category_transactions",
]
