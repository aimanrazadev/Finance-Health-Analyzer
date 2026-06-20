from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import Category, Friend, FriendMerchantLearning, FriendTransactionLink, Transaction
from app.services.friend_detection_service import (
    compact_friend_key,
    display_friend_name,
    friend_names_match,
    normalize_friend_key,
    transaction_friend_candidate,
)
from app.services.friend_learning_service import save_friend_learning_rule


FRIENDS_CATEGORY_NAMES = {"Friend", "Friends"}


def get_friends_category(db: Session) -> Category | None:
    return (
        db.query(Category)
        .filter(Category.name.in_(FRIENDS_CATEGORY_NAMES))
        .order_by(Category.name.desc())
        .first()
    )


def is_friends_category(db: Session, category_id: int | None) -> bool:
    if category_id is None:
        return False
    category = db.query(Category).filter(Category.id == category_id).first()
    return bool(category and category.name in FRIENDS_CATEGORY_NAMES)


def merge_duplicate_friends(db: Session, user_id: int) -> None:
    """Merge dirty duplicate rows into one normalized friend record."""
    friends = (
        db.query(Friend)
        .filter(Friend.user_id == user_id)
        .order_by(Friend.id.asc())
        .all()
    )
    keeper_by_compact: dict[str, Friend] = {}

    for friend in friends:
        normalized = normalize_friend_key(friend.normalized_name or friend.name)
        compact = compact_friend_key(normalized)
        if not compact:
            continue

        friend.normalized_name = normalized
        friend.name = display_friend_name(friend.name)
        keeper = keeper_by_compact.get(compact)
        if keeper is None:
            keeper_by_compact[compact] = friend
            continue

        (
            db.query(FriendTransactionLink)
            .filter(FriendTransactionLink.friend_id == friend.id)
            .update({FriendTransactionLink.friend_id: keeper.id}, synchronize_session=False)
        )
        (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.friend_id == friend.id)
            .update({Transaction.friend_id: keeper.id}, synchronize_session=False)
        )
        db.delete(friend)


def find_existing_friend(db: Session, user_id: int, name: str) -> Friend | None:
    normalized = normalize_friend_key(name)
    compact = compact_friend_key(name)
    if not normalized:
        return None

    exact = (
        db.query(Friend)
        .filter(
            Friend.user_id == user_id,
            Friend.normalized_name == normalized,
        )
        .first()
    )
    if exact:
        return exact

    candidates = db.query(Friend).filter(Friend.user_id == user_id).all()
    for friend in candidates:
        if compact and compact_friend_key(friend.normalized_name or friend.name) == compact:
            return friend
        if friend_names_match(friend.name, name, threshold=93):
            return friend
    return None


def get_or_create_friend(db: Session, user_id: int, name: str) -> Friend:
    normalized = normalize_friend_key(name)
    if not normalized:
        raise ValueError("Friend name is required.")

    merge_duplicate_friends(db, user_id)
    friend = find_existing_friend(db, user_id, normalized)
    if friend:
        friend.name = display_friend_name(friend.name or normalized)
        friend.normalized_name = normalize_friend_key(friend.name)
        friend.is_hidden = False
        return friend

    friend = Friend(
        user_id=user_id,
        name=display_friend_name(normalized),
        normalized_name=normalized,
        is_hidden=False,
    )
    db.add(friend)
    db.flush()
    return friend


def transaction_matches_friend(transaction: Transaction, friend: Friend) -> bool:
    candidate = transaction_friend_candidate(transaction)
    if friend_names_match(friend.normalized_name or friend.name, candidate):
        return True

    haystack = " ".join(
        value for value in [
            transaction.description,
            transaction.merchant,
            transaction.extracted_merchant,
        ]
        if value
    )
    return friend_names_match(friend.normalized_name or friend.name, haystack)


def _ensure_transaction_link(db: Session, user_id: int, friend: Friend, transaction: Transaction) -> bool:
    for pending in db.new:
        if not isinstance(pending, FriendTransactionLink):
            continue
        if pending.friend_id == friend.id and pending.transaction_id == transaction.id:
            return False

    existing = (
        db.query(FriendTransactionLink)
        .filter(
            FriendTransactionLink.friend_id == friend.id,
            FriendTransactionLink.transaction_id == transaction.id,
        )
        .first()
    )
    if existing:
        return False

    db.add(
        FriendTransactionLink(
            user_id=user_id,
            friend_id=friend.id,
            transaction_id=transaction.id,
        )
    )
    return True


def mark_transaction_as_friend(db: Session, user_id: int, friend: Friend, transaction: Transaction) -> bool:
    """Attach one transaction to a friend and remove it from review."""
    friends_category = get_friends_category(db)
    if friends_category:
        transaction.category_id = friends_category.id

    transaction.friend_id = friend.id
    transaction.is_friend_transaction = True
    transaction.normalized_friend_name = friend.normalized_name
    transaction.category_confidence = 0.95
    transaction.categorization_method = "friend_match"
    transaction.review_status = "approved"
    transaction.is_needs_review = False
    transaction.extracted_merchant = transaction_friend_candidate(transaction) or transaction.extracted_merchant
    transaction.merchant = transaction.extracted_merchant or transaction.merchant

    save_friend_learning_rule(db, user_id, friend.id, friend.normalized_name)
    return _ensure_transaction_link(db, user_id, friend, transaction)


def refresh_friend_stats(db: Session, friend: Friend) -> Friend:
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == friend.user_id, Transaction.friend_id == friend.id)
        .all()
    )
    friend.transaction_count = len(rows)
    friend.total_amount = sum(float(row.amount or 0) for row in rows)
    dates = [row.date for row in rows if isinstance(row.date, datetime)]
    friend.last_transaction_at = max(dates) if dates else None
    return friend


def link_matching_transactions(db: Session, user_id: int, friend: Friend) -> int:
    """Find and link every historical transaction that matches this friend."""
    linked_count = 0
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    for transaction in transactions:
        if transaction_matches_friend(transaction, friend):
            if mark_transaction_as_friend(db, user_id, friend, transaction):
                linked_count += 1
    refresh_friend_stats(db, friend)
    return linked_count


def create_or_update_friend_from_name(db: Session, user_id: int, name: str) -> tuple[Friend, int]:
    friend = get_or_create_friend(db, user_id, name)
    save_friend_learning_rule(db, user_id, friend.id, friend.normalized_name)
    linked_count = link_matching_transactions(db, user_id, friend)
    refresh_friend_stats(db, friend)
    return friend, linked_count


def create_or_update_friend_from_transaction(db: Session, user_id: int, transaction: Transaction) -> tuple[Friend, int]:
    name = transaction_friend_candidate(transaction)
    if not name:
        raise ValueError("Could not extract a friend name from this transaction.")
    friend, linked_count = create_or_update_friend_from_name(db, user_id, name)
    mark_transaction_as_friend(db, user_id, friend, transaction)
    refresh_friend_stats(db, friend)
    return friend, linked_count


def auto_attach_transaction_if_friend(db: Session, user_id: int, transaction: Transaction) -> Friend | None:
    """Attach future transactions to the best learned friend match, if one exists."""
    if transaction.friend_id:
        return db.query(Friend).filter(Friend.id == transaction.friend_id, Friend.user_id == user_id).first()

    candidate = transaction_friend_candidate(transaction)
    learned_rules = (
        db.query(FriendMerchantLearning, Friend)
        .join(Friend, FriendMerchantLearning.friend_id == Friend.id)
        .filter(
            FriendMerchantLearning.user_id == user_id,
            Friend.user_id == user_id,
            Friend.is_hidden == False,  # noqa: E712
        )
        .all()
    )
    for rule, friend in learned_rules:
        if friend_names_match(rule.normalized_merchant, candidate) or transaction_matches_friend(transaction, friend):
            mark_transaction_as_friend(db, user_id, friend, transaction)
            rule.usage_count = (rule.usage_count or 0) + 1
            rule.last_used_at = datetime.utcnow()
            refresh_friend_stats(db, friend)
            return friend

    friends = db.query(Friend).filter(Friend.user_id == user_id, Friend.is_hidden == False).all()  # noqa: E712
    for friend in friends:
        if transaction_matches_friend(transaction, friend):
            mark_transaction_as_friend(db, user_id, friend, transaction)
            refresh_friend_stats(db, friend)
            return friend
    return None


def get_friend_detail(db: Session, user_id: int, friend_id: int) -> tuple[Friend | None, list[Transaction]]:
    friend = (
        db.query(Friend)
        .filter(Friend.id == friend_id, Friend.user_id == user_id, Friend.is_hidden == False)  # noqa: E712
        .first()
    )
    if not friend:
        return None, []

    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.friend_id == friend.id)
        .order_by(Transaction.date.desc())
        .all()
    )
    return refresh_friend_stats(db, friend), transactions


def get_friend_dashboard(db: Session, user_id: int) -> dict:
    friends = (
        db.query(Friend)
        .filter(Friend.user_id == user_id, Friend.is_hidden == False)  # noqa: E712
        .order_by(Friend.name.asc())
        .all()
    )
    for friend in friends:
        refresh_friend_stats(db, friend)

    linked_count = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.is_friend_transaction == True)  # noqa: E712
        .count()
    )
    return {
        "active_friends": len(friends),
        "linked_transactions": linked_count,
        "friends": [
            {
                "id": friend.id,
                "user_id": friend.user_id,
                "name": friend.name,
                "normalized_name": friend.normalized_name,
                "transaction_count": friend.transaction_count or 0,
                "total_amount": float(friend.total_amount or 0),
                "last_transaction_at": friend.last_transaction_at,
                "is_hidden": bool(friend.is_hidden),
                "created_at": friend.created_at,
            }
            for friend in friends
        ],
    }


def hide_friend(db: Session, user_id: int, friend_id: int) -> Friend | None:
    friend = db.query(Friend).filter(Friend.id == friend_id, Friend.user_id == user_id).first()
    if not friend:
        return None
    friend.is_hidden = True
    return friend
