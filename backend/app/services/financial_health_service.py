from calendar import monthrange
from datetime import datetime
from statistics import mean

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Category, FinancialScore, Transaction


def _month_bounds(month: int, year: int) -> tuple[datetime, datetime]:
    return datetime(year, month, 1), datetime(year, month, monthrange(year, month)[1], 23, 59, 59)


def _previous_month(month: int, year: int) -> tuple[int, int]:
    if month == 1:
        return 12, year - 1
    return month - 1, year


def _clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _status_label(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Average"
    return "Needs Improvement"


def _cash_flow(db: Session, user_id: int, month: int, year: int) -> tuple[float, float]:
    start, end = _month_bounds(month, year)
    income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.user_id == user_id, Transaction.transaction_type == "income", Transaction.date >= start, Transaction.date <= end)
        .scalar()
    )
    expenses = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense", Transaction.date >= start, Transaction.date <= end)
        .scalar()
    )
    return float(income or 0), float(expenses or 0)


def _score_savings_rate(income: float, expenses: float) -> tuple[int, str]:
    if income <= 0:
        return 45, "Add income transactions to measure savings rate accurately."
    savings_rate = ((income - expenses) / income) * 100
    if savings_rate >= 30:
        score = 100
    elif savings_rate >= 20:
        score = 85
    elif savings_rate >= 10:
        score = 70
    elif savings_rate >= 0:
        score = 50
    else:
        score = 25
    return score, f"Savings rate is {savings_rate:.1f}% for this month."


def _score_expense_control(income: float, expenses: float) -> tuple[int, str]:
    if income <= 0:
        return 45, "Add income transactions to compare expenses against income."
    expense_ratio = expenses / income
    if expense_ratio <= 0.60:
        score = 100
    elif expense_ratio <= 0.80:
        score = 78
    elif expense_ratio <= 1:
        score = 55
    else:
        score = 25
    return score, f"Expenses used {expense_ratio * 100:.1f}% of income this month."


def _score_spending_stability(db: Session, user_id: int, month: int, year: int, current_expenses: float) -> tuple[int, str]:
    values = []
    cursor_month, cursor_year = month, year
    for _ in range(3):
        cursor_month, cursor_year = _previous_month(cursor_month, cursor_year)
        _income, expenses = _cash_flow(db, user_id, cursor_month, cursor_year)
        if expenses > 0:
            values.append(expenses)
    if not values:
        return 60, "More monthly history will improve spending stability scoring."
    baseline = mean(values)
    change = abs(current_expenses - baseline) / baseline if baseline else 0
    score = _clamp_score(100 - change * 120)
    return score, f"Current expenses compared with recent monthly average of INR {baseline:.2f}."


def _score_subscription_impact(db: Session, user_id: int, month: int, year: int, income: float) -> tuple[int, str]:
    start, end = _month_bounds(month, year)
    subscription_total = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start,
            Transaction.date <= end,
            func.lower(Category.name) == "subscriptions",
        )
        .scalar()
        or 0
    )

    if subscription_total <= 0:
        return 100, "No Subscriptions category payments found this month."
    if income <= 0:
        return 60, f"Subscriptions category payments total INR {subscription_total:.2f}; add income to score impact."

    share = subscription_total / income * 100
    if share <= 5:
        score = 95
    elif share <= 10:
        score = 80
    elif share <= 20:
        score = 60
    else:
        score = 35
    return score, f"Subscriptions category payments are {share:.1f}% of monthly income."


def _tips_for_scores(scores: dict[str, int]) -> list[str]:
    tips = []
    if scores["savings_score"] < 70:
        tips.append("Try moving a fixed amount to savings immediately after income arrives.")
    if scores["expense_score"] < 70:
        tips.append("Review your largest spending categories and cut the least useful recurring costs first.")
    if scores["stability_score"] < 70:
        tips.append("Review unusual spending spikes and separate one-time purchases from recurring expenses.")
    if scores["subscription_score"] < 70:
        tips.append("Review recurring subscriptions and cancel services you no longer use.")
    return tips or ["Your finances look steady. Keep tracking monthly habits to maintain this score."]


def _breakdown(label: str, score: int, description: str) -> dict:
    return {
        "label": label,
        "score": score,
        "status": _status_label(score),
        "description": description,
    }


def calculate_financial_health_score(db: Session, user_id: int, month: int, year: int) -> dict:
    income, expenses = _cash_flow(db, user_id, month, year)
    savings_score, savings_description = _score_savings_rate(income, expenses)
    expense_score, expense_description = _score_expense_control(income, expenses)
    stability_score, stability_description = _score_spending_stability(db, user_id, month, year, expenses)
    subscription_score, subscription_description = _score_subscription_impact(db, user_id, month, year, income)

    overall_score = _clamp_score(
        savings_score * 0.35
        + expense_score * 0.30
        + stability_score * 0.20
        + subscription_score * 0.15
    )

    record = FinancialScore(
        user_id=user_id,
        overall_score=overall_score,
        savings_score=savings_score,
        budget_score=expense_score,
        stability_score=stability_score,
        subscription_score=subscription_score,
        debt_score=100,
        emergency_fund_score=0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    scores = {
        "savings_score": savings_score,
        "expense_score": expense_score,
        "stability_score": stability_score,
        "subscription_score": subscription_score,
    }
    return {
        "id": record.id,
        "month": month,
        "year": year,
        "overall_score": overall_score,
        "status_label": _status_label(overall_score),
        "savings_score": savings_score,
        "budget_score": expense_score,
        "stability_score": stability_score,
        "subscription_score": subscription_score,
        "debt_score": 100,
        "emergency_fund_score": 0,
        "breakdown": [
            _breakdown("Savings rate", savings_score, savings_description),
            _breakdown("Expense control", expense_score, expense_description),
            _breakdown("Spending stability", stability_score, stability_description),
            _breakdown("Subscription impact", subscription_score, subscription_description),
        ],
        "improvement_tips": _tips_for_scores(scores),
        "calculated_at": record.calculated_at,
    }
