from statistics import mean

from sqlalchemy.orm import Session

from app.models.models import FinancialScore
from app.services.analytics_service import (
    build_dashboard_summary,
    previous_period,
    subscription_summary,
)


def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _status(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Average"
    return "Needs Improvement"


def _savings_rate_score(income: float, savings: float) -> tuple[int, str]:
    if income <= 0:
        return 0, "Add income transactions to measure the intentional savings rate."
    rate = savings / income * 100
    if rate >= 20:
        score = 100
    elif rate >= 15:
        score = 85
    elif rate >= 10:
        score = 70
    elif rate >= 5:
        score = 50
    elif rate > 0:
        score = 35
    else:
        score = 20
    return score, f"Savings and Investments equal {rate:.1f}% of income."


def _subscription_score(income: float, monthly_cost: float) -> tuple[int, str]:
    if monthly_cost <= 0:
        return 100, "No recurring subscription cost was detected in this period."
    if income <= 0:
        return 20, f"Subscriptions total INR {monthly_cost:,.2f}; income is needed to measure their impact."
    share = monthly_cost / income * 100
    if share <= 5:
        score = 100
    elif share <= 10:
        score = 80
    elif share <= 15:
        score = 60
    elif share <= 20:
        score = 40
    else:
        score = 20
    return score, f"Subscriptions equal {share:.1f}% of income."


def _lifestyle_expenses(summary) -> float:
    return max(float(summary.total_expenses) - float(summary.total_savings), 0.0)


def _stability_score(db: Session, user_id: int, month: int, year: int, current: float) -> tuple[int, str]:
    if month == -1:
        return 60, "Select a month or year to compare spending stability over time."
    history: list[float] = []
    cursor_month, cursor_year = month, year
    for _ in range(3):
        cursor_month, cursor_year = previous_period(cursor_month, cursor_year)
        previous = build_dashboard_summary(db, user_id, cursor_month, cursor_year)
        value = _lifestyle_expenses(previous)
        if value > 0:
            history.append(value)
    if not history:
        return 60, "More prior-period spending data is needed for a stable comparison."
    baseline = mean(history)
    variation = abs(current - baseline) / baseline if baseline else 0
    if variation <= 0.10:
        score = 100
    elif variation <= 0.25:
        score = 80
    elif variation <= 0.45:
        score = 55
    else:
        score = 30
    return score, f"Lifestyle spending is compared with a recent average of INR {baseline:,.2f}."


def _balance_score(current_balance: float, income: float) -> tuple[int, str]:
    if current_balance <= 0:
        return 20, "The latest bank closing balance for this period is zero or negative."
    if income <= 0:
        return 50, f"Latest bank closing balance is INR {current_balance:,.2f}; add income to measure its strength."
    ratio = current_balance / income
    if ratio >= 1:
        score = 100
    elif ratio >= 0.50:
        score = 85
    elif ratio >= 0.25:
        score = 70
    elif ratio >= 0.10:
        score = 55
    else:
        score = 40
    return score, f"Latest bank closing balance equals {ratio * 100:.1f}% of period income."


def _breakdown(label: str, score: int, description: str) -> dict:
    return {"label": label, "score": score, "status": _status(score), "description": description}


def _tips(scores: dict[str, int]) -> list[str]:
    tips: list[str] = []
    if scores["savings_score"] < 70:
        tips.append("Categorize planned transfers under Savings or Investments to track intentional saving habits.")
    if scores["subscription_score"] < 70:
        tips.append("Review recurring subscriptions and remove services you no longer use.")
    if scores["stability_score"] < 70:
        tips.append("Review unusual spending spikes and separate one-time purchases from recurring costs.")
    if scores["balance_score"] < 70:
        tips.append("Build a larger closing-balance buffer before taking on new recurring commitments.")
    return tips or ["Your core financial signals are steady. Keep categorizing transactions consistently."]


def calculate_financial_health_score(db: Session, user_id: int, month: int, year: int) -> dict:
    summary = build_dashboard_summary(db, user_id, month, year)
    recurring = subscription_summary(db, user_id, month, year)
    savings_score, savings_description = _savings_rate_score(summary.total_income, summary.total_savings)
    subscription_score, subscription_description = _subscription_score(
        summary.total_income,
        float(recurring["monthly_total"]),
    )
    stability_score, stability_description = _stability_score(
        db,
        user_id,
        month,
        year,
        _lifestyle_expenses(summary),
    )
    balance_score, balance_description = _balance_score(summary.current_balance, summary.total_income)
    overall_score = _clamp((savings_score + subscription_score + stability_score + balance_score) / 4)

    record = FinancialScore(
        user_id=user_id,
        overall_score=overall_score,
        savings_score=savings_score,
        budget_score=balance_score,
        stability_score=stability_score,
        subscription_score=subscription_score,
        debt_score=balance_score,
        emergency_fund_score=balance_score,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    scores = {
        "savings_score": savings_score,
        "subscription_score": subscription_score,
        "stability_score": stability_score,
        "balance_score": balance_score,
    }
    return {
        "id": record.id,
        "month": month,
        "year": year,
        "overall_score": overall_score,
        "status_label": _status(overall_score),
        **scores,
        "breakdown": [
            _breakdown("Savings rate", savings_score, savings_description),
            _breakdown("Subscription control", subscription_score, subscription_description),
            _breakdown("Spending stability", stability_score, stability_description),
            _breakdown("Financial balance", balance_score, balance_description),
        ],
        "improvement_tips": _tips(scores),
        "calculated_at": record.calculated_at,
    }
