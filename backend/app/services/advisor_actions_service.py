import re
from calendar import month_name
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import Category, Transaction
from app.schemas.schemas import AdvisorActionResponse
from app.services.categorization import categorize_transaction
from app.services.dashboard_summary_service import build_dashboard_summary
from app.services.financial_analytics_service import (
    build_category_analytics,
    build_merchant_analytics_detail,
    build_subscription_analytics,
)
from app.services.merchant_extractor_service import extract_transaction_merchant


MONTH_LOOKUP = {name.lower(): index for index, name in enumerate(month_name) if name}


def detect_action_intent(message: str) -> str:
    text = message.lower()
    if any(word in text for word in ("show", "find", "search", "list")) and "transaction" in text:
        return "search_transactions"
    if any(word in text for word in ("add", "create", "record")) and "transaction" in text:
        return "create_transaction"
    if any(word in text for word in ("change", "update", "mark", "categorize")) and "category" in text:
        return "update_category"
    if "report" in text or "summary" in text:
        return "generate_report"
    return "none"


def extract_action_filters(message: str) -> dict[str, Any]:
    text = message.lower()
    filters: dict[str, Any] = {}
    amount_match = re.search(r"(?:above|over|greater than|>)\s*(?:inr|rs|₹)?\s*([0-9,]+(?:\.\d+)?)", text)
    if amount_match:
        filters["amount_gt"] = float(amount_match.group(1).replace(",", ""))
    amount_lt_match = re.search(r"(?:below|under|less than|<)\s*(?:inr|rs|₹)?\s*([0-9,]+(?:\.\d+)?)", text)
    if amount_lt_match:
        filters["amount_lt"] = float(amount_lt_match.group(1).replace(",", ""))
    for month, number in MONTH_LOOKUP.items():
        if month in text:
            filters["month"] = number
            break
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        filters["year"] = int(year_match.group(1))

    merchant_match = re.search(r"(?:all|show|find|search|list)\s+([a-z0-9 .&'-]+?)\s+transactions", text)
    if merchant_match:
        merchant = re.sub(r"^(all|the|my)\s+", "", merchant_match.group(1).strip(), flags=re.I)
        filters["merchant"] = merchant.title()
    elif "from " in text:
        after_from = text.split("from ", 1)[1]
        filters["merchant"] = re.split(r"\s+(?:above|over|below|under|in|from)\s+", after_from)[0].strip().title()
    return filters


def search_transactions_from_filters(db: Session, user_id: int, filters: dict[str, Any]) -> list[Transaction]:
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    merchant = filters.get("merchant")
    if merchant:
        term = f"%{merchant}%"
        query = query.filter(or_(Transaction.merchant.ilike(term), Transaction.description.ilike(term)))
    if filters.get("amount_gt") is not None:
        query = query.filter(Transaction.amount > filters["amount_gt"])
    if filters.get("amount_lt") is not None:
        query = query.filter(Transaction.amount < filters["amount_lt"])
    if filters.get("month"):
        query = query.filter(Transaction.date >= datetime(filters.get("year") or datetime.now().year, filters["month"], 1))
        next_month = filters["month"] + 1
        next_year = filters.get("year") or datetime.now().year
        if next_month == 13:
            next_month = 1
            next_year += 1
        query = query.filter(Transaction.date < datetime(next_year, next_month, 1))
    elif filters.get("year"):
        query = query.filter(Transaction.date >= datetime(filters["year"], 1, 1), Transaction.date < datetime(filters["year"] + 1, 1, 1))
    return query.order_by(Transaction.date.desc()).limit(25).all()


def create_transaction_from_text(db: Session, user_id: int, message: str) -> Transaction | None:
    amount_match = re.search(r"(?:inr|rs|₹)?\s*([0-9,]+(?:\.\d+)?)", message.lower())
    if not amount_match:
        return None
    amount = float(amount_match.group(1).replace(",", ""))
    merchant = extract_transaction_merchant(message, None)
    result = categorize_transaction(db, user_id, message, amount, "expense", merchant)
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        description=message[:255],
        merchant=merchant,
        extracted_merchant=merchant,
        transaction_type="expense",
        date=datetime.now(),
        category_id=result["category_id"] if isinstance(result["category_id"], int) else None,
        category_confidence=float(result["confidence"]),
        categorization_method=str(result["method"]),
        review_status=str(result["review_status"]),
        is_needs_review=str(result["review_status"]) == "needs_review",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def update_category_from_text(db: Session, user_id: int, message: str) -> tuple[int, str]:
    categories = db.query(Category).all()
    target = next((category for category in categories if category.name.lower() in message.lower()), None)
    filters = extract_action_filters(message)
    merchant = filters.get("merchant")
    if not target or not merchant:
        return 0, "Mention both merchant name and target category."
    transactions = search_transactions_from_filters(db, user_id, {"merchant": merchant})
    for transaction in transactions:
        transaction.category_id = target.id
        transaction.category_confidence = 1.0
        transaction.categorization_method = "manual"
        transaction.review_status = "approved"
        transaction.is_needs_review = False
    db.commit()
    return len(transactions), f"Updated {len(transactions)} {merchant} transactions to {target.name}."


def generate_report(db: Session, user_id: int, message: str) -> dict[str, Any]:
    filters = extract_action_filters(message)
    month = filters.get("month") or datetime.now().month
    year = filters.get("year") or datetime.now().year
    summary = build_dashboard_summary(db, user_id, month, year)
    categories = build_category_analytics(db, user_id, month, year)
    merchants = build_merchant_analytics_detail(db, user_id, month, year)
    subscriptions = build_subscription_analytics(db, user_id, month, year)
    return {
        "period": {"month": month, "year": year},
        "income": summary.total_income,
        "expenses": summary.total_expenses,
        "savings": summary.total_savings,
        "savings_rate": summary.savings_rate,
        "top_category": categories.highest_spending_category,
        "top_merchant": merchants.top_merchants[0].merchant_name if merchants.top_merchants else None,
        "subscriptions": subscriptions.subscription_count,
    }


def run_advisor_action(db: Session, user_id: int, message: str) -> AdvisorActionResponse:
    intent = detect_action_intent(message)
    filters = extract_action_filters(message)

    if intent == "search_transactions":
        transactions = search_transactions_from_filters(db, user_id, filters)
        return AdvisorActionResponse(
            action_type="search",
            intent=intent,
            filters=filters,
            message=f"{len(transactions)} transactions found.",
            transactions=transactions,
        )
    if intent == "create_transaction":
        transaction = create_transaction_from_text(db, user_id, message)
        return AdvisorActionResponse(
            action_type="create",
            intent=intent,
            filters=filters,
            message="Transaction created." if transaction else "I could not find an amount to create the transaction.",
            transactions=[transaction] if transaction else [],
        )
    if intent == "update_category":
        count, response_message = update_category_from_text(db, user_id, message)
        return AdvisorActionResponse(
            action_type="update_category",
            intent=intent,
            filters=filters,
            message=response_message,
            transactions=[],
            report={"updated_count": count},
        )
    if intent == "generate_report":
        report = generate_report(db, user_id, message)
        return AdvisorActionResponse(
            action_type="report",
            intent=intent,
            filters=filters,
            message="Report generated from your stored analytics.",
            report=report,
        )

    return AdvisorActionResponse(
        action_type="none",
        intent="none",
        filters=filters,
        message="No safe app action was detected. Ask the advisor normally for guidance.",
    )
