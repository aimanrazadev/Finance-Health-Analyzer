from calendar import monthrange
from datetime import datetime
from statistics import mean

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Budget, Debt, FinancialScore, SavingsGoal, Transaction

SUBSCRIPTION_TERMS = ("subscription", "netflix", "spotify", "youtube", "prime", "apple music")


def _month_bounds(month: int, year: int) -> tuple[datetime, datetime]:
    return datetime(year, month, 1), datetime(year, month, monthrange(year, month)[1], 23, 59, 59)


def _previous_month(month: int, year: int) -> tuple[int, int]:
    if month == 1:
        return 12, year - 1
    return month - 1, year


def _period(month: int, year: int) -> str:
    return f"{year:04d}-{month:02d}"


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


def _score_budget_control(db: Session, user_id: int, month: int, year: int) -> tuple[int, str]:
    budgets = db.query(Budget).filter(Budget.user_id == user_id, Budget.period == _period(month, year), Budget.is_active == True).all()  # noqa: E712
    if not budgets:
        return 55, "Create monthly budgets to improve budget control scoring."

    usage_scores = []
    for budget in budgets:
        start, end = _month_bounds(month, year)
        spent = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_type == "expense",
                Transaction.date >= start,
                Transaction.date <= end,
            )
            .scalar()
        )
        usage = float(spent or 0) / float(budget.amount or 1)
        usage_scores.append(_clamp_score(100 - max(0, usage - 0.75) * 160))
    score = _clamp_score(mean(usage_scores))
    return score, f"{len(budgets)} active budgets analyzed for the selected month."


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


def _score_debt(db: Session, user_id: int) -> tuple[int, str]:
    unpaid_total = (
        db.query(func.coalesce(func.sum(Debt.amount), 0))
        .filter(Debt.user_id == user_id, Debt.status != "paid")
        .scalar()
    )
    unpaid_total = float(unpaid_total or 0)
    if unpaid_total <= 0:
        return 100, "No open personal debt records found."
    if unpaid_total <= 5000:
        return 75, f"Open personal debt records total INR {unpaid_total:.2f}."
    if unpaid_total <= 25000:
        return 55, f"Open personal debt records total INR {unpaid_total:.2f}."
    return 35, f"Open personal debt records total INR {unpaid_total:.2f}."


def _score_subscription_impact(db: Session, user_id: int, month: int, year: int, income: float) -> tuple[int, str]:
    start, end = _month_bounds(month, year)
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .all()
    )
    subscription_total = 0.0
    for transaction in transactions:
        searchable = f"{transaction.description or ''} {transaction.merchant or ''}".lower()
        if transaction.is_recurring or any(term in searchable for term in SUBSCRIPTION_TERMS):
            subscription_total += float(transaction.amount or 0)

    if subscription_total <= 0:
        return 100, "No subscription-like payments detected this month."
    if income <= 0:
        return 60, f"Subscription-like payments total INR {subscription_total:.2f}; add income to score impact."

    share = subscription_total / income * 100
    if share <= 5:
        score = 95
    elif share <= 10:
        score = 80
    elif share <= 20:
        score = 60
    else:
        score = 35
    return score, f"Subscription-like payments are {share:.1f}% of monthly income."


def _score_emergency_fund(db: Session, user_id: int, monthly_expenses: float) -> tuple[int, str]:
    emergency_saved = (
        db.query(func.coalesce(func.sum(SavingsGoal.current_amount), 0))
        .filter(SavingsGoal.user_id == user_id, SavingsGoal.name.ilike("%emergency%"))
        .scalar()
    )
    emergency_saved = float(emergency_saved or 0)
    if monthly_expenses <= 0:
        return 50, "Add expenses and an emergency fund goal for a better score."
    months_covered = emergency_saved / monthly_expenses
    score = _clamp_score((months_covered / 6) * 100)
    return score, f"Emergency savings cover about {months_covered:.1f} months of expenses."


def _tips_for_scores(scores: dict[str, int]) -> list[str]:
    tips = []
    if scores["savings_score"] < 70:
        tips.append("Try moving a fixed amount to savings immediately after income arrives.")
    if scores["budget_score"] < 70:
        tips.append("Set or adjust category budgets for your highest spending areas.")
    if scores["stability_score"] < 70:
        tips.append("Review unusual spending spikes and separate one-time purchases from recurring expenses.")
    if scores["subscription_score"] < 70:
        tips.append("Review recurring subscriptions and cancel services you no longer use.")
    if scores["debt_score"] < 70:
        tips.append("Track repayments against friend or debt balances to reduce open obligations.")
    if scores["emergency_fund_score"] < 70:
        tips.append("Create an emergency fund goal and target at least three months of expenses.")
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
    budget_score, budget_description = _score_budget_control(db, user_id, month, year)
    stability_score, stability_description = _score_spending_stability(db, user_id, month, year, expenses)
    subscription_score, subscription_description = _score_subscription_impact(db, user_id, month, year, income)
    debt_score, debt_description = _score_debt(db, user_id)
    emergency_score, emergency_description = _score_emergency_fund(db, user_id, expenses)

    overall_score = _clamp_score(
        savings_score * 0.25
        + budget_score * 0.22
        + stability_score * 0.16
        + subscription_score * 0.12
        + debt_score * 0.15
        + emergency_score * 0.10
    )

    record = FinancialScore(
        user_id=user_id,
        overall_score=overall_score,
        savings_score=savings_score,
        budget_score=budget_score,
        stability_score=stability_score,
        subscription_score=subscription_score,
        debt_score=debt_score,
        emergency_fund_score=emergency_score,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    scores = {
        "savings_score": savings_score,
        "budget_score": budget_score,
        "stability_score": stability_score,
        "subscription_score": subscription_score,
        "debt_score": debt_score,
        "emergency_fund_score": emergency_score,
    }
    return {
        "id": record.id,
        "month": month,
        "year": year,
        "overall_score": overall_score,
        "status_label": _status_label(overall_score),
        **scores,
        "breakdown": [
            _breakdown("Savings rate", savings_score, savings_description),
            _breakdown("Budget control", budget_score, budget_description),
            _breakdown("Spending stability", stability_score, stability_description),
            _breakdown("Subscription impact", subscription_score, subscription_description),
            _breakdown("Debt control", debt_score, debt_description),
            _breakdown("Emergency fund", emergency_score, emergency_description),
        ],
        "improvement_tips": _tips_for_scores(scores),
        "calculated_at": record.calculated_at,
    }
