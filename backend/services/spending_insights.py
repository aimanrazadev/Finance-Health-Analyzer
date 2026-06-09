from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ai.llm_client import LLMClient
from models import AiInsight, Category, Transaction

SUBSCRIPTION_KEYWORDS = ["subscription", "netflix", "spotify", "youtube", "prime", "apple music"]


def previous_month(month: int, year: int) -> tuple[int, int]:
    if month == 1:
        return 12, year - 1
    return month - 1, year


def get_expense_total(db: Session, user_id: int, month: int, year: int) -> float:
    return float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == month,
            func.year(Transaction.date) == year,
        )
        .scalar()
        or 0
    )


def get_income_total(db: Session, user_id: int, month: int, year: int) -> float:
    return float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
            func.month(Transaction.date) == month,
            func.year(Transaction.date) == year,
        )
        .scalar()
        or 0
    )


def get_category_totals(db: Session, user_id: int, month: int, year: int) -> list[dict[str, Any]]:
    rows = (
        db.query(
            Category.id.label("category_id"),
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == month,
            func.year(Transaction.date) == year,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    return [
        {
            "category_id": row.category_id,
            "category_name": row.category_name,
            "total": float(row.total or 0),
        }
        for row in rows
    ]


def detect_subscription_transactions(db: Session, user_id: int, month: int, year: int) -> list[dict[str, Any]]:
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == month,
            func.year(Transaction.date) == year,
        )
        .all()
    )
    matches = []
    for transaction in transactions:
        text = f"{transaction.description or ''} {transaction.merchant or ''}".lower()
        if any(keyword in text for keyword in SUBSCRIPTION_KEYWORDS):
            matches.append(
                {
                    "description": transaction.description,
                    "merchant": transaction.merchant,
                    "amount": float(transaction.amount),
                }
            )
    return matches


def detect_unusual_spending(db: Session, user_id: int, month: int, year: int, current_total: float) -> dict[str, Any] | None:
    rows = (
        db.query(
            func.month(Transaction.date).label("month_number"),
            func.year(Transaction.date).label("year_number"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
        )
        .group_by(func.year(Transaction.date), func.month(Transaction.date))
        .order_by(func.year(Transaction.date).desc(), func.month(Transaction.date).desc())
        .limit(6)
        .all()
    )
    previous_totals = [
        float(row.total or 0)
        for row in rows
        if not (int(row.month_number) == month and int(row.year_number) == year)
    ]
    if len(previous_totals) < 2:
        return None

    average = sum(previous_totals) / len(previous_totals)
    if average and current_total > average * 1.25:
        return {
            "average": round(average, 2),
            "current": round(current_total, 2),
            "increase_percentage": round(((current_total - average) / average) * 100, 2),
        }
    return None


def build_spending_summary(db: Session, user_id: int, month: int, year: int) -> dict[str, Any]:
    prev_month, prev_year = previous_month(month, year)
    current_expenses = get_expense_total(db, user_id, month, year)
    previous_expenses = get_expense_total(db, user_id, prev_month, prev_year)
    current_income = get_income_total(db, user_id, month, year)
    category_totals = get_category_totals(db, user_id, month, year)
    previous_categories = {
        item["category_name"]: item["total"]
        for item in get_category_totals(db, user_id, prev_month, prev_year)
    }

    category_increases = []
    for item in category_totals:
        previous_total = previous_categories.get(item["category_name"], 0)
        if previous_total and item["total"] > previous_total * 1.15:
            category_increases.append(
                {
                    "category": item["category_name"],
                    "current": item["total"],
                    "previous": previous_total,
                    "increase_percentage": round(((item["total"] - previous_total) / previous_total) * 100, 2),
                }
            )

    return {
        "month": month,
        "year": year,
        "income": current_income,
        "expenses": current_expenses,
        "previous_expenses": previous_expenses,
        "expense_change_percentage": round(((current_expenses - previous_expenses) / previous_expenses) * 100, 2) if previous_expenses else None,
        "highest_category": category_totals[0] if category_totals else None,
        "category_totals": category_totals,
        "category_increases": category_increases,
        "unusual_spending": detect_unusual_spending(db, user_id, month, year, current_expenses),
        "subscriptions": detect_subscription_transactions(db, user_id, month, year),
    }


def build_insight_prompt(summary: dict[str, Any]) -> str:
    return (
        "Analyze this personal finance summary and produce 4 short, practical insights.\n"
        "Avoid risky investment advice. Focus on spending, budgeting, subscriptions, and saving.\n\n"
        f"Summary: {summary}"
    )


def fallback_insights(summary: dict[str, Any]) -> list[dict[str, str]]:
    insights = []
    if summary["highest_category"]:
        category = summary["highest_category"]
        insights.append({
            "type": "spending",
            "text": f"Your highest spending category is {category['category_name']} at INR {category['total']:.2f}.",
        })

    if summary["expense_change_percentage"] is not None:
        direction = "increased" if summary["expense_change_percentage"] >= 0 else "decreased"
        insights.append({
            "type": "comparison",
            "text": f"Your expenses {direction} by {abs(summary['expense_change_percentage']):.1f}% compared with last month.",
        })

    if summary["category_increases"]:
        item = summary["category_increases"][0]
        insights.append({
            "type": "category_increase",
            "text": f"{item['category']} spending rose by {item['increase_percentage']:.1f}% compared with last month.",
        })

    if summary["unusual_spending"]:
        item = summary["unusual_spending"]
        insights.append({
            "type": "anomaly",
            "text": f"This month looks unusually high: INR {item['current']:.2f} versus a recent average of INR {item['average']:.2f}.",
        })

    if summary["subscriptions"]:
        total = sum(item["amount"] for item in summary["subscriptions"])
        insights.append({
            "type": "subscription",
            "text": f"Detected {len(summary['subscriptions'])} subscription-like payments totaling INR {total:.2f}.",
        })

    if not insights:
        insights.append({
            "type": "spending",
            "text": "Add more transactions to generate stronger spending insights for this period.",
        })

    return insights[:5]


def parse_ai_text(ai_text: str | None, summary: dict[str, Any]) -> list[dict[str, str]]:
    if not ai_text:
        return fallback_insights(summary)

    lines = [line.strip(" -0123456789.") for line in ai_text.splitlines() if line.strip()]
    parsed = [{"type": "ai", "text": line} for line in lines if line]
    return parsed[:5] or fallback_insights(summary)


def generate_and_store_insights(db: Session, user_id: int, month: int, year: int, regenerate: bool = False) -> list[AiInsight]:
    if regenerate:
        (
            db.query(AiInsight)
            .filter(AiInsight.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.flush()

    summary = build_spending_summary(db, user_id, month, year)
    prompt = build_insight_prompt(summary)
    ai_text = LLMClient().generate_text(prompt)
    insights = parse_ai_text(ai_text, summary)

    saved = []
    provider = "AI" if ai_text else "RuleBasedFallback"
    for insight in insights:
        record = AiInsight(
            user_id=user_id,
            insight_text=insight["text"],
            insight_type=insight["type"],
        )
        db.add(record)
        saved.append(record)
    db.commit()

    for record in saved:
        db.refresh(record)
    return saved


def get_latest_insights(db: Session, user_id: int) -> list[AiInsight]:
    return (
        db.query(AiInsight)
        .filter(AiInsight.user_id == user_id)
        .order_by(AiInsight.created_at.desc())
        .limit(10)
        .all()
    )
