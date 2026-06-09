from calendar import monthrange
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ai.llm_client import LLMClient
from models import Budget, Category, Transaction


FOCUS_CATEGORIES = {"Food", "Shopping", "Subscriptions", "Entertainment"}
PRIORITY_WEIGHT = {"High": 3, "Medium": 2, "Low": 1}


def _month_bounds(month: int, year: int) -> tuple[datetime, datetime]:
    """Return inclusive datetime bounds for a month."""
    last_day = monthrange(year, month)[1]
    return datetime(year, month, 1), datetime(year, month, last_day, 23, 59, 59)


def _budget_period(month: int, year: int) -> str:
    """Match the period format used by the budget planner."""
    return f"{year:04d}-{month:02d}"


def _priority_for_savings(amount: float) -> str:
    """Translate potential monthly savings into a simple impact priority."""
    if amount >= 3000:
        return "High"
    if amount >= 750:
        return "Medium"
    return "Low"


def _impact_score(priority: str, potential_savings: float) -> float:
    """Rank recommendations by priority first, then expected monthly savings."""
    return round((PRIORITY_WEIGHT.get(priority, 1) * 10000) + potential_savings, 2)


def _recommendation(
    key: str,
    title: str,
    text: str,
    category_name: str | None,
    potential_savings: float,
    reason: str,
    priority: str | None = None,
) -> dict[str, Any]:
    """Create a normalized recommendation record for API responses."""
    resolved_priority = priority or _priority_for_savings(potential_savings)
    return {
        "id": key,
        "title": title,
        "recommendation_text": text,
        "category_name": category_name,
        "priority": resolved_priority,
        "potential_savings": round(max(potential_savings, 0), 2),
        "impact_score": _impact_score(resolved_priority, potential_savings),
        "reason": reason,
    }


def _category_spending(db: Session, user_id: int, month: int, year: int) -> list[dict[str, Any]]:
    """Calculate expense totals grouped by category for the selected month."""
    start_date, end_date = _month_bounds(month, year)
    rows = (
        db.query(
            Transaction.category_id,
            Category.name.label("category_name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .group_by(Transaction.category_id, Category.name)
        .all()
    )
    return [
        {
            "category_id": row.category_id,
            "category_name": row.category_name or "Uncategorized",
            "total": float(row.total or 0),
        }
        for row in rows
    ]


def _cash_flow(db: Session, user_id: int, month: int, year: int) -> tuple[float, float, float]:
    """Return income, expenses, and savings rate for the selected month."""
    start_date, end_date = _month_bounds(month, year)
    income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .scalar()
    ) or 0
    expenses = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .scalar()
    ) or 0
    savings_rate = ((float(income) - float(expenses)) / float(income) * 100) if income else 0
    return float(income), float(expenses), round(savings_rate, 2)


def _ai_rewrite_recommendations(recommendations: list[dict[str, Any]], month: int, year: int) -> list[dict[str, Any]]:
    """Optionally use the configured LLM to make rule-generated text clearer."""
    if not recommendations:
        return recommendations

    prompt = (
        "Rewrite these budget recommendations in concise, practical language. "
        "Keep the same order, titles, priorities, and potential savings. "
        "Return one line per item as: title | recommendation.\n"
        f"Period: {month}/{year}\n"
    )
    for item in recommendations:
        prompt += f"- {item['title']} | {item['recommendation_text']}\n"

    text = LLMClient().generate_text(prompt)
    if not text:
        return recommendations

    rewritten = [line.strip() for line in text.splitlines() if "|" in line]
    if len(rewritten) < len(recommendations):
        return recommendations

    for item, line in zip(recommendations, rewritten):
        _, recommendation_text = line.split("|", 1)
        item["recommendation_text"] = recommendation_text.strip() or item["recommendation_text"]
    return recommendations


def generate_budget_recommendations(db: Session, user_id: int, month: int, year: int) -> dict[str, Any]:
    """Generate ranked budget recommendations from budgets, spending mix, and savings rate."""
    income, expenses, savings_rate = _cash_flow(db, user_id, month, year)
    spending = _category_spending(db, user_id, month, year)
    spending_by_category = {item["category_name"]: item for item in spending}
    total_expenses = expenses or sum(item["total"] for item in spending)
    recommendations: list[dict[str, Any]] = []

    budgets = (
        db.query(Budget, Category)
        .join(Category, Budget.category_id == Category.id)
        .filter(
            Budget.user_id == user_id,
            Budget.period == _budget_period(month, year),
            Budget.is_active == True,  # noqa: E712
        )
        .all()
    )
    for budget, category in budgets:
        spent = spending_by_category.get(category.name, {}).get("total", 0)
        if spent > budget.amount:
            overage = spent - budget.amount
            recommendations.append(_recommendation(
                key=f"over-budget-{budget.id}",
                title=f"Reduce {category.name.lower()} spending",
                text=f"{category.name} is over budget by INR {overage:.2f}. Aim to bring it back under the monthly limit.",
                category_name=category.name,
                potential_savings=overage,
                priority="High",
                reason="over_budget_category",
            ))

    if income and expenses / income >= 0.85:
        target_expenses = income * 0.75
        recommendations.append(_recommendation(
            key="expense-income-ratio",
            title="Lower spending as a share of income",
            text=f"Expenses are {expenses / income * 100:.1f}% of income. Try keeping monthly spending closer to 75% of income.",
            category_name=None,
            potential_savings=max(expenses - target_expenses, 0),
            priority="High",
            reason="high_expense_to_income_ratio",
        ))

    if income and savings_rate < 20:
        target_savings = income * 0.20
        current_savings = income - expenses
        recommendations.append(_recommendation(
            key="low-savings-rate",
            title="Improve monthly savings rate",
            text=f"Savings rate is {savings_rate:.1f}%. Build toward a 20% savings target for this month.",
            category_name=None,
            potential_savings=max(target_savings - current_savings, 0),
            priority="High" if savings_rate < 10 else "Medium",
            reason="low_savings_rate",
        ))

    for category_name in FOCUS_CATEGORIES:
        item = spending_by_category.get(category_name)
        if not item or not total_expenses:
            continue
        share = item["total"] / total_expenses * 100
        threshold = 25 if category_name in {"Food", "Shopping"} else 12
        if share >= threshold:
            saving_rate = 0.20 if category_name in {"Food", "Shopping"} else 0.30
            recommendations.append(_recommendation(
                key=f"high-{category_name.lower()}",
                title=f"Trim {category_name.lower()} spending",
                text=f"{category_name} makes up {share:.1f}% of monthly expenses. Set a tighter cap for the next few weeks.",
                category_name=category_name,
                potential_savings=item["total"] * saving_rate,
                reason="high_category_spending",
            ))

    recommendations = sorted(
        recommendations,
        key=lambda item: (item["impact_score"], item["potential_savings"]),
        reverse=True,
    )
    recommendations = _ai_rewrite_recommendations(recommendations[:6], month, year)

    if not recommendations:
        recommendations.append(_recommendation(
            key="steady-month",
            title="Keep your current budget discipline",
            text="No major over-budget or low-savings signals were detected for this month.",
            category_name=None,
            potential_savings=0,
            priority="Low",
            reason="no_major_risk_detected",
        ))

    return {
        "month": month,
        "year": year,
        "total_income": income,
        "total_expenses": expenses,
        "savings_rate": savings_rate,
        "recommendations": recommendations,
    }
