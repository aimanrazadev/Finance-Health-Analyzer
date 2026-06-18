from calendar import monthrange
from datetime import datetime
from statistics import mean

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models.models import Category, Transaction
from app.schemas.schemas import (
    CategoryBreakdownItem,
    ChartDataPoint,
    DashboardChartsResponse,
    DashboardSummary,
    IncomeExpenseChart,
    MonthlySpendingPoint,
    MonthlyTrendPoint,
    MonthlyTrendResponse,
)


INVESTMENT_CATEGORY_NAMES = {"investments", "investment", "mutual funds", "stocks"}
SALARY_CATEGORY_NAMES = {"salary", "salaries"}
SUBSCRIPTION_CATEGORY_NAMES = {"subscriptions", "subscription"}


def _period(month: int, year: int) -> str:
    return f"{year:04d}-{month:02d}"


def _month_bounds(month: int, year: int) -> tuple[datetime, datetime]:
    last_day = monthrange(year, month)[1]
    return datetime(year, month, 1), datetime(year, month, last_day, 23, 59, 59)


def _period_bounds(month: int, year: int, day: int | None = None) -> tuple[datetime, datetime]:
    """Month -1 means lifetime, month 0 means the full selected year."""
    if day and month > 0:
        return datetime(year, month, day), datetime(year, month, day, 23, 59, 59)
    if month == -1:
        return datetime(1900, 1, 1), datetime(9999, 12, 31, 23, 59, 59)
    if month == 0:
        return datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59)
    return _month_bounds(month, year)


def _previous_period(month: int, year: int) -> tuple[int, int]:
    if month == -1:
        return -1, year
    if month == 0:
        return 0, year - 1
    if month == 1:
        return 12, year - 1
    return month - 1, year


def _transaction_query(db: Session, user_id: int, month: int, year: int, day: int | None = None):
    start_date, end_date = _period_bounds(month, year, day)
    return db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    )


def _income_total(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> float:
    start_date, end_date = _period_bounds(month, year, day)
    rows = (
        db.query(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == user_id, Transaction.date >= start_date, Transaction.date <= end_date)
        .all()
    )
    # Salary category is treated as income even if an import labels the row imperfectly.
    return round(
        sum(
            float(transaction.amount or 0)
            for transaction, category in rows
            if transaction.transaction_type == "income" or (category and category.name.lower() in SALARY_CATEGORY_NAMES)
        ),
        2,
    )


def _expense_and_investment_totals(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> tuple[float, float]:
    start_date, end_date = _period_bounds(month, year, day)
    rows = (
        db.query(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type.in_(["expense", "savings"]),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .all()
    )
    expense_total = 0.0
    investment_total = 0.0
    for transaction, category in rows:
        amount = float(transaction.amount or 0)
        category_name = (category.name if category else "").lower()
        if category_name in INVESTMENT_CATEGORY_NAMES:
            investment_total += amount
        else:
            expense_total += amount
    return round(expense_total, 2), round(investment_total, 2)


def _change_percentage(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 2)


def _category_rows(db: Session, user_id: int, month: int, year: int, include_investments: bool = False, day: int | None = None):
    start_date, end_date = _period_bounds(month, year, day)
    rows = (
        db.query(
            Transaction.category_id,
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            Category.color.label("color"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type.in_(["expense", "savings"] if include_investments else ["expense"]),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .group_by(Transaction.category_id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    if include_investments:
        return rows
    return [row for row in rows if row.category_name.lower() not in INVESTMENT_CATEGORY_NAMES]


def _status_label(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Average"
    return "Needs Improvement"


def _expense_history(db: Session, user_id: int, month: int, year: int, periods: int = 3) -> list[float]:
    values = []
    cursor_month, cursor_year = month, year
    for _ in range(periods):
        cursor_month, cursor_year = _previous_period(cursor_month, cursor_year)
        if cursor_month == 0:
            break
        expenses, _investments = _expense_and_investment_totals(db, user_id, cursor_month, cursor_year)
        values.append(expenses)
    return values


def _spending_stability_score(current_expenses: float, history: list[float]) -> int:
    usable_history = [value for value in history if value > 0]
    if not usable_history:
        return 60
    average_expense = mean(usable_history)
    if average_expense <= 0:
        return 60
    variation = abs(current_expenses - average_expense) / average_expense
    if variation <= 0.10:
        return 100
    if variation <= 0.25:
        return 80
    if variation <= 0.45:
        return 55
    return 30


def _financial_health_snapshot(
    income: float,
    expenses: float,
    savings_rate: float,
    subscription_total: float,
    spending_stability_score: int,
) -> tuple[int, str, str]:
    if income <= 0:
        score = 35 if expenses > 0 else 0
        return score, "Needs Improvement", "Add income transactions to calculate a reliable health score."

    if savings_rate >= 30:
        savings_score = 100
    elif savings_rate >= 20:
        savings_score = 85
    elif savings_rate >= 10:
        savings_score = 65
    elif savings_rate >= 0:
        savings_score = 45
    else:
        savings_score = 20

    expense_ratio = expenses / income
    if expense_ratio <= 0.60:
        spending_score = 100
    elif expense_ratio <= 0.80:
        spending_score = 75
    elif expense_ratio <= 1:
        spending_score = 50
    else:
        spending_score = 20

    subscription_ratio = subscription_total / income
    if subscription_ratio <= 0.05:
        subscription_score = 100
    elif subscription_ratio <= 0.10:
        subscription_score = 75
    elif subscription_ratio <= 0.18:
        subscription_score = 50
    else:
        subscription_score = 25

    score = int(round(
        savings_score * 0.35
        + spending_score * 0.30
        + spending_stability_score * 0.20
        + subscription_score * 0.15
    ))
    score_parts = {
        "savings rate": savings_score,
        "expense control": spending_score,
        "subscription load": subscription_score,
        "spending stability": spending_stability_score,
    }
    weakest_area = min(score_parts, key=score_parts.get)
    if score >= 80:
        reason = "Strong savings, controlled expenses, and stable spending."
    elif weakest_area == "savings rate":
        reason = "Savings rate is pulling the score down."
    elif weakest_area == "expense control":
        reason = "Expenses are taking a high share of income."
    elif weakest_area == "subscription load":
        reason = "Recurring subscriptions are heavy for this income."
    else:
        reason = "Spending is changing sharply compared with recent months."
    return score, _status_label(score), reason


def _top_merchant(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> str | None:
    start_date, end_date = _period_bounds(month, year, day)
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, "Unknown merchant")
    row = (
        db.query(merchant_name.label("merchant"), func.coalesce(func.sum(Transaction.amount), 0).label("total"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            func.lower(func.coalesce(Category.name, "")).notin_(INVESTMENT_CATEGORY_NAMES),
        )
        .group_by(merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
        .first()
    )
    return row.merchant if row else None


def _subscription_summary(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> dict[str, float | int]:
    """Infer recurring load from transactions categorized as Subscriptions."""
    start_date, end_date = _period_bounds(month, year, day)
    rows = (
        db.query(
            func.coalesce(Transaction.extracted_merchant, Transaction.merchant, Transaction.description).label("merchant"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            func.lower(Category.name).in_(SUBSCRIPTION_CATEGORY_NAMES),
        )
        .group_by(func.coalesce(Transaction.extracted_merchant, Transaction.merchant, Transaction.description))
        .all()
    )
    return {
        "subscription_count": len(rows),
        "monthly_total": round(sum(float(row.total or 0) for row in rows), 2),
    }


def _latest_statement_balance(db: Session, user_id: int) -> float:
    """Use the newest statement row balance as the user's current account balance."""
    latest_balance_row = (
        db.query(Transaction.balance)
        .filter(
            Transaction.user_id == user_id,
            Transaction.balance.isnot(None),
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .first()
    )
    return round(float(latest_balance_row.balance or 0), 2) if latest_balance_row else 0.0


def build_dashboard_summary(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> DashboardSummary:
    income = _income_total(db, user_id, month, year, day)
    expenses, investment_amount = _expense_and_investment_totals(db, user_id, month, year, day)
    account_balance = _latest_statement_balance(db, user_id)
    remaining_money = income - expenses - investment_amount
    total_savings = investment_amount + remaining_money + account_balance

    category_breakdown = [
        CategoryBreakdownItem(
            category_id=row.category_id,
            category_name=row.category_name,
            total=round(float(row.total or 0), 2),
            color=row.color,
        )
    for row in _category_rows(db, user_id, month, year, day=day)
    ]

    prev_month, prev_year = _previous_period(month, year)
    previous_income = _income_total(db, user_id, prev_month, prev_year)
    previous_expenses, previous_investments = _expense_and_investment_totals(db, user_id, prev_month, prev_year)
    previous_savings = previous_investments + (previous_income - previous_expenses - previous_investments)
    savings_trend = ((total_savings - previous_savings) / abs(previous_savings) * 100) if previous_savings else 0
    savings_rate = (total_savings / income * 100) if income else 0
    if savings_rate >= 30:
        savings_status = "Good"
    elif savings_rate >= 10:
        savings_status = "Average"
    else:
        savings_status = "Poor"

    subscription_summary = _subscription_summary(db, user_id, month, year, day)
    spending_stability_score = _spending_stability_score(expenses, _expense_history(db, user_id, month, year))
    financial_health_score, financial_health_status, financial_health_reason = _financial_health_snapshot(
        income,
        expenses,
        savings_rate,
        subscription_summary["monthly_total"],
        spending_stability_score,
    )

    return DashboardSummary(
        month=month,
        year=year,
        total_income=round(income, 2),
        total_expenses=round(expenses, 2),
        account_balance=round(account_balance, 2),
        investment_amount=round(investment_amount, 2),
        remaining_money=round(remaining_money, 2),
        total_savings=round(total_savings, 2),
        investment_savings=round(investment_amount, 2),
        remaining_balance_savings=round(remaining_money, 2),
        effective_savings=round(total_savings, 2),
        savings_rate=round(savings_rate, 2),
        effective_savings_rate=round(savings_rate, 2),
        monthly_savings_trend=round(savings_trend, 2),
        savings_status=savings_status,
        transaction_count=_transaction_query(db, user_id, month, year, day).count(),
        top_category=category_breakdown[0].category_name if category_breakdown else None,
        top_merchant=_top_merchant(db, user_id, month, year, day),
        recurring_subscription_count=subscription_summary["subscription_count"],
        recurring_subscription_total=subscription_summary["monthly_total"],
        financial_health_score=financial_health_score,
        financial_health_status=financial_health_status,
        financial_health_reason=financial_health_reason,
        budget_health_score=0,
        category_breakdown=category_breakdown,
    )


def build_dashboard_charts(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> DashboardChartsResponse:
    category_breakdown = [
        ChartDataPoint(name=row.category_name, value=round(float(row.total or 0), 2), color=row.color)
        for row in _category_rows(db, user_id, month, year, day=day)
    ]

    monthly_trends = build_monthly_trends(db, user_id, year).trends
    monthly_by_name = {row.month: row.expenses for row in monthly_trends}

    start_date, end_date = _period_bounds(month, year, day)
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, "Unknown merchant")
    merchant_rows = (
        db.query(merchant_name.label("name"), func.coalesce(func.sum(Transaction.amount), 0).label("value"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            func.lower(func.coalesce(Category.name, "")).notin_(INVESTMENT_CATEGORY_NAMES),
        )
        .group_by(merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
        .all()
    )

    return DashboardChartsResponse(
        month=month,
        year=year,
        category_breakdown=category_breakdown,
        income_vs_expense=IncomeExpenseChart(
            income=_income_total(db, user_id, month, year),
            expenses=_expense_and_investment_totals(db, user_id, month, year, day)[0],
        ),
        monthly_spending=[
            MonthlySpendingPoint(
                month=datetime(year, month_number, 1).strftime("%b"),
                expenses=round(monthly_by_name.get(datetime(year, month_number, 1).strftime("%b"), 0), 2),
            )
            for month_number in range(1, 13)
        ],
        monthly_trends=monthly_trends,
        top_merchants=[
            ChartDataPoint(name=row.name, value=round(float(row.value or 0), 2))
            for row in merchant_rows
        ],
    )


def build_merchant_analytics(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> list[ChartDataPoint]:
    return build_dashboard_charts(db, user_id, month, year, day).top_merchants


def build_monthly_trends(db: Session, user_id: int, year: int) -> MonthlyTrendResponse:
    trends = []
    for month_number in range(1, 13):
        income = _income_total(db, user_id, month_number, year)
        expenses, investments = _expense_and_investment_totals(db, user_id, month_number, year)
        trends.append(MonthlyTrendPoint(
            month=datetime(year, month_number, 1).strftime("%b"),
            income=round(income, 2),
            expenses=round(expenses, 2),
            savings=round(income - expenses, 2),
            investments=round(investments, 2),
        ))

    today = datetime.today()
    comparison_month = min(today.month, 12) if year == today.year else 12
    current = trends[comparison_month - 1]
    if comparison_month == 1:
        previous_income = _income_total(db, user_id, 12, year - 1)
        previous_expenses, previous_investments = _expense_and_investment_totals(db, user_id, 12, year - 1)
        previous_savings = previous_income - previous_expenses
    else:
        previous = trends[comparison_month - 2]
        previous_income = previous.income
        previous_expenses = previous.expenses
        previous_savings = previous.savings
        previous_investments = previous.investments

    return MonthlyTrendResponse(
        year=year,
        trends=trends,
        income_change_percentage=_change_percentage(current.income, previous_income),
        expense_change_percentage=_change_percentage(current.expenses, previous_expenses),
        savings_change_percentage=_change_percentage(current.savings, previous_savings),
        investment_change_percentage=_change_percentage(current.investments, previous_investments),
    )
