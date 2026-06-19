from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.models import Category, Friend, FriendMerchantLearning, FriendTransactionLink, Transaction
from app.services.friend_detection_service import (
    canonical_friend_display_name,
    detect_friend_for_transaction,
    extract_friend_name_from_text,
    normalize_friend_name,
)
from app.services.friend_learning_service import save_friend_learning_rule
from app.services.merchant_extractor_service import extract_transaction_merchant


def get_friends_category_id(db: Session) -> int | None:
    category = db.query(Category).filter(Category.name == "Friends").first()
    return category.id if category else None


def _friend_name_from_transaction(transaction: Transaction) -> str | None:
    return (
        extract_friend_name_from_text(transaction.description, transaction.extracted_merchant or transaction.merchant)
        or extract_transaction_merchant(transaction.description, transaction.extracted_merchant or transaction.merchant)
        or canonical_friend_display_name(transaction.extracted_merchant or transaction.merchant or transaction.description)
    )


def merge_duplicate_friends(db: Session, user_id: int, normalized_name: str) -> Friend | None:
    """Collapse duplicate friend rows into one canonical record for a user."""
    duplicates = (
        db.query(Friend)
        .filter(Friend.user_id == user_id, Friend.normalized_name == normalized_name)
        .order_by(Friend.id.asc())
        .all()
    )
    if not duplicates:
        return None

    primary = duplicates[0]
    primary.is_active = True
    primary.name = canonical_friend_display_name(primary.name) or primary.name

    duplicate_ids = [friend.id for friend in duplicates[1:]]
    if not duplicate_ids:
        return primary

    db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.friend_id.in_(duplicate_ids),
    ).update({Transaction.friend_id: primary.id, Transaction.is_friend_transaction: True}, synchronize_session=False)

    db.query(FriendTransactionLink).filter(
        FriendTransactionLink.user_id == user_id,
        FriendTransactionLink.friend_id.in_(duplicate_ids),
    ).update({FriendTransactionLink.friend_id: primary.id}, synchronize_session=False)

    db.query(FriendMerchantLearning).filter(
        FriendMerchantLearning.user_id == user_id,
        FriendMerchantLearning.friend_id.in_(duplicate_ids),
    ).update({FriendMerchantLearning.friend_id: primary.id}, synchronize_session=False)

    for duplicate in duplicates[1:]:
        duplicate.is_active = False
        duplicate.normalized_name = f"{duplicate.normalized_name}__merged_{duplicate.id}"

    _dedupe_friend_links(db, user_id, primary.id)
    _dedupe_friend_learning(db, user_id, primary.id)
    return primary


def normalize_existing_friends(db: Session, user_id: int | None = None) -> int:
    """Normalize old friend rows and merge existing dirty duplicates."""
    query = db.query(Friend)
    if user_id is not None:
        query = query.filter(Friend.user_id == user_id)

    changed = 0
    seen: set[tuple[int, str]] = set()
    for friend in query.order_by(Friend.id.asc()).all():
        if friend.is_active is False and "__merged_" in (friend.normalized_name or ""):
            continue

        display_name = canonical_friend_display_name(friend.name) or friend.name.strip()
        normalized_name = normalize_friend_name(display_name)
        if not normalized_name:
            continue
        if friend.name != display_name:
            friend.name = display_name
            changed += 1
        if friend.normalized_name != normalized_name:
            friend.normalized_name = normalized_name
            changed += 1
        key = (friend.user_id, normalized_name)
        if key not in seen:
            seen.add(key)
            primary = merge_duplicate_friends(db, friend.user_id, normalized_name)
            if primary:
                changed += 1
    return changed


def _dedupe_friend_links(db: Session, user_id: int, friend_id: int) -> None:
    seen: set[int] = set()
    rows = (
        db.query(FriendTransactionLink)
        .filter(FriendTransactionLink.user_id == user_id, FriendTransactionLink.friend_id == friend_id)
        .order_by(FriendTransactionLink.id.asc())
        .all()
    )
    for row in rows:
        if row.transaction_id in seen:
            db.delete(row)
        else:
            seen.add(row.transaction_id)


def _dedupe_friend_learning(db: Session, user_id: int, friend_id: int) -> None:
    seen: dict[str, FriendMerchantLearning] = {}
    rows = (
        db.query(FriendMerchantLearning)
        .filter(FriendMerchantLearning.user_id == user_id, FriendMerchantLearning.friend_id == friend_id)
        .order_by(FriendMerchantLearning.id.asc())
        .all()
    )
    for row in rows:
        normalized = row.normalized_merchant or normalize_friend_name(row.merchant_pattern)
        if normalized in seen:
            seen[normalized].usage_count = (seen[normalized].usage_count or 0) + (row.usage_count or 0)
            db.delete(row)
        else:
            row.normalized_merchant = normalized
            seen[normalized] = row


def create_friend(
    db: Session,
    user_id: int,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
) -> Friend:
    display_name = canonical_friend_display_name(name) or name.strip()
    normalized_name = normalize_friend_name(display_name)
    if not normalized_name:
        raise ValueError("Friend name is required")

    normalize_existing_friends(db, user_id)
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
        friend = merge_duplicate_friends(db, user_id, normalized_name) or friend
        friend.name = display_name
        friend.email = email if email is not None else friend.email
        friend.phone = phone if phone is not None else friend.phone
        friend.notes = notes if notes is not None else friend.notes
        friend.is_active = True
        auto_attach_matching_transactions(db, user_id, friend)
        return friend

    friend = Friend(
        user_id=user_id,
        name=display_name,
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

    friend_name = _friend_name_from_transaction(transaction)
    if friend_name:
        friend.name = canonical_friend_display_name(friend_name) or friend.name
        friend.normalized_name = normalize_friend_name(friend.name)
        friend = merge_duplicate_friends(db, user_id, friend.normalized_name) or friend
        transaction.friend_id = friend.id

    save_friend_learning_rule(
        db,
        user_id,
        friend.id,
        friend_name or transaction.extracted_merchant or transaction.merchant or transaction.description,
    )
    return changed


def auto_attach_matching_transactions(db: Session, user_id: int, friend: Friend) -> int:
    """Attach all existing transactions that mention the saved friend's name."""
    normalize_existing_friends(db, user_id)
    friend = merge_duplicate_friends(db, user_id, friend.normalized_name or normalize_friend_name(friend.name)) or friend
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

    repaired_count = normalize_existing_friends(db)
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
    for transaction in rows:
        friend_name = _friend_name_from_transaction(transaction)
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
            )
            .order_by(Friend.id.asc())
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
        else:
            friend.is_active = True
            friend = merge_duplicate_friends(db, transaction.user_id, normalized_name) or friend

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
    "merge_duplicate_friends",
    "normalize_friend_name",
    "normalize_existing_friends",
    "sync_friends_category_transactions",
]
