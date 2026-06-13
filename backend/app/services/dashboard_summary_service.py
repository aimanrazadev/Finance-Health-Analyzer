from calendar import monthrange
from datetime import datetime
from statistics import mean

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models.models import AccountBalance, Budget, Category, SuggestedBudget, Transaction
from app.schemas.schemas import (
    BudgetUsageChartItem,
    CategoryBreakdownItem,
    ChartDataPoint,
    DashboardChartsResponse,
    DashboardSummary,
    IncomeExpenseChart,
    MonthlySpendingPoint,
    SuggestedBudgetResponse,
)
from app.services.subscription_service import list_active_subscriptions


INVESTMENT_CATEGORY_NAMES = {"investments", "investment", "mutual funds", "stocks"}


def _period(month: int, year: int) -> str:
    return f"{year:04d}-{month:02d}"


def _month_bounds(month: int, year: int) -> tuple[datetime, datetime]:
    last_day = monthrange(year, month)[1]
    return datetime(year, month, 1), datetime(year, month, last_day, 23, 59, 59)


def _period_bounds(month: int, year: int) -> tuple[datetime, datetime]:
    """Month 0 means the full selected year."""
    if month == 0:
        return datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59)
    return _month_bounds(month, year)


def _previous_period(month: int, year: int) -> tuple[int, int]:
    if month == 0:
        return 0, year - 1
    if month == 1:
        return 12, year - 1
    return month - 1, year


def _transaction_query(db: Session, user_id: int, month: int, year: int):
    start_date, end_date = _period_bounds(month, year)
    return db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    )


def _sum_transactions(db: Session, user_id: int, month: int, year: int, transaction_type: str) -> float:
    start_date, end_date = _period_bounds(month, year)
    return float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .scalar()
        or 0
    )


def _category_rows(db: Session, user_id: int, month: int, year: int):
    start_date, end_date = _period_bounds(month, year)
    return (
        db.query(
            Transaction.category_id,
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
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
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )


def _investment_savings(category_breakdown: list[CategoryBreakdownItem]) -> float:
    return round(
        sum(
            item.total
            for item in category_breakdown
            if item.category_name.lower() in INVESTMENT_CATEGORY_NAMES
        ),
        2,
    )


def _latest_balance(db: Session, user_id: int) -> float:
    balance = (
        db.query(AccountBalance)
        .filter(AccountBalance.user_id == user_id)
        .order_by(AccountBalance.updated_at.desc(), AccountBalance.recorded_at.desc())
        .first()
    )
    return float(balance.balance_amount) if balance else 0.0


def _top_merchant(db: Session, user_id: int, month: int, year: int) -> str | None:
    start_date, end_date = _period_bounds(month, year)
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, "Unknown merchant")
    row = (
        db.query(merchant_name.label("merchant"), func.coalesce(func.sum(Transaction.amount), 0).label("total"))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .group_by(merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
        .first()
    )
    return row.merchant if row else None


def _budget_usage_rows(db: Session, user_id: int, month: int, year: int) -> list[BudgetUsageChartItem]:
    if month == 0:
        return []
    rows: list[BudgetUsageChartItem] = []
    budgets = (
        db.query(Budget, Category)
        .join(Category, Budget.category_id == Category.id)
        .filter(Budget.user_id == user_id, Budget.period == _period(month, year), Budget.is_active == True)  # noqa: E712
        .all()
    )
    start_date, end_date = _month_bounds(month, year)
    for budget, category in budgets:
        spent = float(
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_type == "expense",
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
            .scalar()
            or 0
        )
        limit = float(budget.amount or 0)
        percentage_used = (spent / limit * 100) if limit else 0
        rows.append(BudgetUsageChartItem(
            category_id=budget.category_id,
            category_name=category.name,
            limit=round(limit, 2),
            spent=round(spent, 2),
            remaining=round(limit - spent, 2),
            percentage_used=round(percentage_used, 2),
            status="over_budget" if spent > limit else "warning" if percentage_used >= 90 else "on_track",
        ))
    return rows


def _budget_health_score(budget_rows: list[BudgetUsageChartItem]) -> int:
    if not budget_rows:
        return 0
    scores = []
    for row in budget_rows:
        if row.percentage_used <= 75:
            scores.append(100)
        elif row.percentage_used <= 100:
            scores.append(max(40, 100 - (row.percentage_used - 75) * 2.4))
        else:
            scores.append(max(0, 40 - (row.percentage_used - 100)))
    return int(round(mean(scores)))


def build_dashboard_summary(db: Session, user_id: int, month: int, year: int) -> DashboardSummary:
    income = _sum_transactions(db, user_id, month, year, "income")
    expenses = _sum_transactions(db, user_id, month, year, "expense")
    total_savings = income - expenses

    category_breakdown = [
        CategoryBreakdownItem(
            category_id=row.category_id,
            category_name=row.category_name,
            total=round(float(row.total or 0), 2),
        )
        for row in _category_rows(db, user_id, month, year)
    ]

    investment_savings = _investment_savings(category_breakdown)
    remaining_balance = _latest_balance(db, user_id)
    effective_savings = total_savings + investment_savings + remaining_balance
    prev_month, prev_year = _previous_period(month, year)
    previous_income = _sum_transactions(db, user_id, prev_month, prev_year, "income")
    previous_expenses = _sum_transactions(db, user_id, prev_month, prev_year, "expense")
    previous_savings = previous_income - previous_expenses
    savings_trend = ((total_savings - previous_savings) / abs(previous_savings) * 100) if previous_savings else 0

    subscription_summary = list_active_subscriptions(db, user_id)
    budget_rows = _budget_usage_rows(db, user_id, month, year)

    return DashboardSummary(
        month=month,
        year=year,
        total_income=round(income, 2),
        total_expenses=round(expenses, 2),
        total_savings=round(total_savings, 2),
        investment_savings=investment_savings,
        remaining_balance_savings=round(remaining_balance, 2),
        effective_savings=round(effective_savings, 2),
        savings_rate=round((total_savings / income * 100) if income else 0, 2),
        effective_savings_rate=round((effective_savings / income * 100) if income else 0, 2),
        monthly_savings_trend=round(savings_trend, 2),
        transaction_count=_transaction_query(db, user_id, month, year).count(),
        top_category=category_breakdown[0].category_name if category_breakdown else None,
        top_merchant=_top_merchant(db, user_id, month, year),
        recurring_subscription_count=subscription_summary["subscription_count"],
        recurring_subscription_total=subscription_summary["monthly_total"],
        budget_health_score=_budget_health_score(budget_rows),
        category_breakdown=category_breakdown,
    )


def build_dashboard_charts(db: Session, user_id: int, month: int, year: int) -> DashboardChartsResponse:
    category_breakdown = [
        ChartDataPoint(name=row.category_name, value=round(float(row.total or 0), 2))
        for row in _category_rows(db, user_id, month, year)
    ]

    monthly_rows = (
        db.query(
            extract("month", Transaction.date).label("month_number"),
            func.coalesce(func.sum(Transaction.amount), 0).label("expenses"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= datetime(year, 1, 1),
            Transaction.date <= datetime(year, 12, 31, 23, 59, 59),
        )
        .group_by(extract("month", Transaction.date))
        .order_by(extract("month", Transaction.date))
        .all()
    )
    monthly_by_number = {int(row.month_number): float(row.expenses or 0) for row in monthly_rows}

    start_date, end_date = _period_bounds(month, year)
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, "Unknown merchant")
    merchant_rows = (
        db.query(merchant_name.label("name"), func.coalesce(func.sum(Transaction.amount), 0).label("value"))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
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
            income=_sum_transactions(db, user_id, month, year, "income"),
            expenses=_sum_transactions(db, user_id, month, year, "expense"),
        ),
        monthly_spending=[
            MonthlySpendingPoint(month=datetime(year, month_number, 1).strftime("%b"), expenses=round(monthly_by_number.get(month_number, 0), 2))
            for month_number in range(1, 13)
        ],
        top_merchants=[
            ChartDataPoint(name=row.name, value=round(float(row.value or 0), 2))
            for row in merchant_rows
        ],
    )


def build_budget_usage_chart(db: Session, user_id: int, month: int, year: int) -> list[BudgetUsageChartItem]:
    return _budget_usage_rows(db, user_id, month, year)


def build_subscription_chart(db: Session, user_id: int) -> list[ChartDataPoint]:
    return [
        ChartDataPoint(name=item["name"], value=float(item["value"]))
        for item in list_active_subscriptions(db, user_id)["chart_data"]
    ]


def build_merchant_analytics(db: Session, user_id: int, month: int, year: int) -> list[ChartDataPoint]:
    return build_dashboard_charts(db, user_id, month, year).top_merchants


def generate_suggested_budgets(db: Session, user_id: int, month: int, year: int, store: bool = False) -> list[SuggestedBudgetResponse]:
    """Suggest next budgets from recent average category spending."""
    if month == 0:
        month = datetime.today().month
    suggestions: list[SuggestedBudgetResponse] = []
    current_period = _period(month, year)

    categories = db.query(Category).filter(func.lower(Category.name).notin_(["salary", "investments"])).all()
    for category in categories:
        totals = []
        cursor_month, cursor_year = month, year
        for _ in range(3):
            if cursor_month == 1:
                cursor_month, cursor_year = 12, cursor_year - 1
            else:
                cursor_month -= 1
            start_date, end_date = _month_bounds(cursor_month, cursor_year)
            total = float(
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.category_id == category.id,
                    Transaction.transaction_type == "expense",
                    Transaction.date >= start_date,
                    Transaction.date <= end_date,
                )
                .scalar()
                or 0
            )
            if total:
                totals.append(total)

        average_spend = mean(totals) if totals else 0
        if average_spend <= 0:
            continue

        suggested_amount = round(average_spend * 1.10, 2)
        custom_budget = (
            db.query(Budget)
            .filter(Budget.user_id == user_id, Budget.category_id == category.id, Budget.period == current_period)
            .first()
        )
        record_id = None
        if store:
            record = (
                db.query(SuggestedBudget)
                .filter(SuggestedBudget.user_id == user_id, SuggestedBudget.category_id == category.id, SuggestedBudget.period == current_period)
                .first()
            )
            if not record:
                record = SuggestedBudget(user_id=user_id, category_id=category.id, period=current_period)
                db.add(record)
            record.average_spend = round(average_spend, 2)
            record.suggested_amount = suggested_amount
            record.source = "three_month_average"
            db.flush()
            record_id = record.id

        suggestions.append(SuggestedBudgetResponse(
            id=record_id,
            category_id=category.id,
            category_name=category.name,
            period=current_period,
            average_spend=round(average_spend, 2),
            suggested_amount=suggested_amount,
            has_custom_budget=custom_budget is not None,
            custom_budget_amount=float(custom_budget.amount) if custom_budget else None,
        ))

    if store:
        db.commit()
    return suggestions
