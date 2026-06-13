import re
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Category, RecurringTransaction, Transaction

KNOWN_SUBSCRIPTION_TERMS = {
    "netflix",
    "spotify",
    "prime",
    "youtube",
    "apple music",
    "subscription",
}


def normalize_subscription_merchant(value: str | None) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _display_merchant(transaction: Transaction) -> str:
    return transaction.merchant or transaction.description[:80] or "Recurring payment"


def _is_known_subscription(transaction: Transaction) -> bool:
    searchable = normalize_subscription_merchant(f"{transaction.merchant or ''} {transaction.description or ''}")
    return any(term in searchable for term in KNOWN_SUBSCRIPTION_TERMS)


def _months_between(first_date: datetime, last_date: datetime) -> int:
    return max((last_date.year - first_date.year) * 12 + last_date.month - first_date.month, 1)


def _amounts_are_consistent(amounts: list[float]) -> bool:
    if len(amounts) < 2:
        return False
    baseline = median(amounts)
    return all(abs(amount - baseline) <= max(20, baseline * 0.12) for amount in amounts)


def _subscriptions_category_id(db: Session) -> int | None:
    category = db.query(Category).filter(func.lower(Category.name) == "subscriptions").first()
    return category.id if category else None


def _upsert_recurring_record(
    db: Session,
    user_id: int,
    merchant_name: str,
    amount: float,
    category_id: int | None,
    latest_date: datetime,
) -> RecurringTransaction:
    record = (
        db.query(RecurringTransaction)
        .filter(
            RecurringTransaction.user_id == user_id,
            RecurringTransaction.description == merchant_name,
            RecurringTransaction.recurrence == "monthly",
        )
        .first()
    )
    next_date = latest_date + timedelta(days=30)
    if record:
        record.amount = amount
        record.category_id = category_id
        record.next_date = next_date
        record.is_active = True
        return record

    record = RecurringTransaction(
        user_id=user_id,
        description=merchant_name,
        amount=amount,
        category_id=category_id,
        recurrence="monthly",
        next_date=next_date,
        is_active=True,
    )
    db.add(record)
    return record


def detect_subscriptions(db: Session, user_id: int) -> dict:
    category_id = _subscriptions_category_id(db)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense")
        .order_by(Transaction.date.asc())
        .all()
    )
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        merchant_key = normalize_subscription_merchant(_display_merchant(transaction))
        if merchant_key:
            grouped[merchant_key].append(transaction)

    active = []
    marked_ids = []
    for _key, rows in grouped.items():
        if len(rows) < 2 and not any(_is_known_subscription(row) for row in rows):
            continue

        amounts = [float(row.amount or 0) for row in rows]
        first_seen = min(row.date for row in rows)
        last_seen = max(row.date for row in rows)
        monthly_span = _months_between(first_seen, last_seen)
        same_amount_monthly = _amounts_are_consistent(amounts)
        known = any(_is_known_subscription(row) for row in rows)
        recurring_enough = len(rows) >= 2 and monthly_span >= 1
        if not known and not (recurring_enough and same_amount_monthly):
            continue

        monthly_amount = round(median(amounts), 2)
        merchant_name = _display_merchant(rows[-1])
        confidence = 0.95 if known and same_amount_monthly else 0.85 if same_amount_monthly else 0.72
        for transaction in rows:
            transaction.is_recurring = True
            if category_id and known:
                transaction.category_id = transaction.category_id or category_id
            marked_ids.append(transaction.id)
        _upsert_recurring_record(db, user_id, merchant_name, monthly_amount, category_id, last_seen)

        active.append({
            "merchant_name": merchant_name,
            "monthly_amount": monthly_amount,
            "transaction_count": len(rows),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "next_expected_date": last_seen + timedelta(days=30),
            "confidence": round(confidence, 2),
            "is_active": True,
            "review_suggestion": "Review this recurring payment if you no longer use it." if len(rows) <= 2 else None,
            "transactions": rows[-6:],
        })

    db.commit()
    active.sort(key=lambda item: item["monthly_amount"], reverse=True)
    monthly_total = round(sum(item["monthly_amount"] for item in active), 2)
    chart_data = [{"name": item["merchant_name"], "value": item["monthly_amount"]} for item in active]
    return {
        "active_subscriptions": active,
        "monthly_total": monthly_total,
        "subscription_count": len(active),
        "marked_transaction_ids": sorted(set(marked_ids)),
        "chart_data": chart_data,
    }


def list_active_subscriptions(db: Session, user_id: int) -> dict:
    return detect_subscriptions(db, user_id)
