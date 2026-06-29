from calendar import monthrange
from datetime import datetime

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


SAVINGS_ALLOCATION_CATEGORY_NAMES = {"savings", "investments"}
SUBSCRIPTION_CATEGORY_NAMES = {"subscription", "subscriptions"}


def period_bounds(month: int, year: int, day: int | None = None) -> tuple[datetime, datetime]:
    """Resolve dashboard filters; -1 is lifetime and 0 is the selected year."""
    if day is not None and month > 0:
        return datetime(year, month, day), datetime(year, month, day, 23, 59, 59)
    if month == -1:
        return datetime(1900, 1, 1), datetime(9999, 12, 31, 23, 59, 59)
    if month == 0:
        return datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59)
    return datetime(year, month, 1), datetime(year, month, monthrange(year, month)[1], 23, 59, 59)


def previous_period(month: int, year: int) -> tuple[int, int]:
    if month == -1:
        return -1, year
    if month == 0:
        return 0, year - 1
    if month == 1:
        return 12, year - 1
    return month - 1, year


def change_percentage(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 2)


def _period_filter(user_id: int, month: int, year: int, day: int | None = None):
    start_date, end_date = period_bounds(month, year, day)
    return (
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    )


def transaction_total(
    db: Session,
    user_id: int,
    transaction_type: str,
    month: int,
    year: int,
    day: int | None = None,
) -> float:
    value = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(*_period_filter(user_id, month, year, day), Transaction.transaction_type == transaction_type)
        .scalar()
    )
    return round(float(value or 0), 2)


def savings_total(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
    category_names: set[str] | None = None,
) -> float:
    names = category_names or SAVINGS_ALLOCATION_CATEGORY_NAMES
    value = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            *_period_filter(user_id, month, year, day),
            Transaction.transaction_type == "expense",
            func.lower(Category.name).in_(names),
        )
        .scalar()
    )
    return round(float(value or 0), 2)


def latest_closing_balance(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> float:
    transaction = (
        db.query(Transaction)
        .filter(*_period_filter(user_id, month, year, day), Transaction.balance.isnot(None))
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .first()
    )
    return round(float(transaction.balance), 2) if transaction and transaction.balance is not None else 0.0


def category_rows(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
):
    return (
        db.query(
            Transaction.category_id,
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            Category.color.label("color"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            *_period_filter(user_id, month, year, day),
            Transaction.transaction_type == "expense",
            func.lower(func.coalesce(Category.name, "")).notin_(SAVINGS_ALLOCATION_CATEGORY_NAMES),
        )
        .group_by(Transaction.category_id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )


def top_merchant(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> str | None:
    merchant_name = func.coalesce(
        Transaction.extracted_merchant,
        Transaction.merchant,
        Transaction.description,
        "Unknown merchant",
    )
    row = (
        db.query(merchant_name.label("merchant"), func.sum(Transaction.amount).label("total"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            *_period_filter(user_id, month, year, day),
            Transaction.transaction_type == "expense",
            func.lower(func.coalesce(Category.name, "")).notin_(SAVINGS_ALLOCATION_CATEGORY_NAMES),
        )
        .group_by(merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
        .first()
    )
    return row.merchant if row else None


def subscription_summary(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> dict[str, float | int]:
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, Transaction.description)
    rows = (
        db.query(merchant_name.label("merchant"), func.sum(Transaction.amount).label("total"))
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            *_period_filter(user_id, month, year, day),
            Transaction.transaction_type == "expense",
            func.lower(Category.name).in_(SUBSCRIPTION_CATEGORY_NAMES),
        )
        .group_by(merchant_name)
        .all()
    )
    return {
        "subscription_count": len(rows),
        "monthly_total": round(sum(float(row.total or 0) for row in rows), 2),
    }


def _savings_status(rate: float) -> str:
    if rate >= 20:
        return "Good"
    if rate >= 10:
        return "Average"
    return "Poor"


def build_dashboard_summary(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> DashboardSummary:
    income = transaction_total(db, user_id, "income", month, year, day)
    expenses = transaction_total(db, user_id, "expense", month, year, day)
    savings = savings_total(db, user_id, month, year, day)
    savings_rate = round((savings / income) * 100, 2) if income else 0.0
    previous_month, previous_year = previous_period(month, year)
    previous_savings = savings_total(db, user_id, previous_month, previous_year)
    savings_trend = change_percentage(savings, previous_savings) or 0.0
    categories = [
        CategoryBreakdownItem(
            category_id=row.category_id,
            category_name=row.category_name,
            total=round(float(row.total or 0), 2),
            color=row.color,
        )
        for row in category_rows(db, user_id, month, year, day)
    ]
    subscriptions = subscription_summary(db, user_id, month, year, day)
    transaction_count = db.query(Transaction).filter(*_period_filter(user_id, month, year, day)).count()

    return DashboardSummary(
        month=month,
        year=year,
        current_balance=latest_closing_balance(db, user_id, month, year, day),
        total_income=income,
        total_expenses=expenses,
        total_savings=savings,
        savings_rate=savings_rate,
        monthly_savings_trend=savings_trend,
        savings_status=_savings_status(savings_rate),
        transaction_count=transaction_count,
        top_category=categories[0].category_name if categories else None,
        top_merchant=top_merchant(db, user_id, month, year, day),
        recurring_subscription_count=int(subscriptions["subscription_count"]),
        recurring_subscription_total=float(subscriptions["monthly_total"]),
        category_breakdown=categories,
    )


def _trend_point(db: Session, user_id: int, month: int, year: int, label: str, day: int | None = None) -> MonthlyTrendPoint:
    income = transaction_total(db, user_id, "income", month, year, day)
    expenses = transaction_total(db, user_id, "expense", month, year, day)
    savings = savings_total(db, user_id, month, year, day)
    investments = savings_total(db, user_id, month, year, day, {"investments"})
    return MonthlyTrendPoint(
        month=label,
        income=income,
        expenses=expenses,
        savings=savings,
        investments=investments,
        savings_rate=round((savings / income) * 100, 2) if income else 0.0,
    )


def period_trends(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> list[MonthlyTrendPoint]:
    if month == -1:
        years = [
            int(row.period_year)
            for row in (
                db.query(extract("year", Transaction.date).label("period_year"))
                .filter(Transaction.user_id == user_id)
                .group_by(extract("year", Transaction.date))
                .order_by(extract("year", Transaction.date))
                .all()
            )
            if row.period_year
        ]
        return [_trend_point(db, user_id, 0, item_year, str(item_year)) for item_year in years]
    if day is not None and month > 0:
        return [_trend_point(db, user_id, month, year, datetime(year, month, day).strftime("%d %b"), day)]
    if month == 0:
        return build_monthly_trends(db, user_id, year).trends
    return [
        _trend_point(db, user_id, month, year, str(day_number), day_number)
        for day_number in range(1, monthrange(year, month)[1] + 1)
    ]


def build_monthly_trends(db: Session, user_id: int, year: int) -> MonthlyTrendResponse:
    trends = [
        _trend_point(db, user_id, month_number, year, datetime(year, month_number, 1).strftime("%b"))
        for month_number in range(1, 13)
    ]
    current_month = min(datetime.today().month, 12) if year == datetime.today().year else 12
    current = trends[current_month - 1]
    previous = trends[current_month - 2] if current_month > 1 else _trend_point(db, user_id, 12, year - 1, "Dec")
    return MonthlyTrendResponse(
        year=year,
        trends=trends,
        income_change_percentage=change_percentage(current.income, previous.income),
        expense_change_percentage=change_percentage(current.expenses, previous.expenses),
        savings_change_percentage=change_percentage(current.savings, previous.savings),
        investment_change_percentage=change_percentage(current.investments, previous.investments),
    )


def build_period_trend_summary(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> MonthlyTrendResponse:
    """Compare the selected dashboard period with its matching prior period."""
    trends = period_trends(db, user_id, month, year, day)
    if month == -1:
        return MonthlyTrendResponse(year=year, trends=trends)

    previous_month, previous_year = previous_period(month, year)
    current_day = day if day is not None and month > 0 else None
    previous_day = None
    if current_day is not None and previous_month > 0:
        previous_day = min(current_day, monthrange(previous_year, previous_month)[1])

    current = _trend_point(db, user_id, month, year, "Current", current_day)
    previous = _trend_point(db, user_id, previous_month, previous_year, "Previous", previous_day)
    return MonthlyTrendResponse(
        year=year,
        trends=trends,
        income_change_percentage=change_percentage(current.income, previous.income),
        expense_change_percentage=change_percentage(current.expenses, previous.expenses),
        savings_change_percentage=change_percentage(current.savings, previous.savings),
        investment_change_percentage=change_percentage(current.investments, previous.investments),
    )


def build_dashboard_charts(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> DashboardChartsResponse:
    categories = [
        ChartDataPoint(name=row.category_name, value=round(float(row.total or 0), 2), color=row.color)
        for row in category_rows(db, user_id, month, year, day)
    ]
    trends = period_trends(db, user_id, month, year, day)
    merchant_rows = build_merchant_analytics(db, user_id, month, year, day)
    yearly_trends = build_monthly_trends(db, user_id, year).trends if month != -1 else []
    return DashboardChartsResponse(
        month=month,
        year=year,
        category_breakdown=categories,
        income_vs_expense=IncomeExpenseChart(
            income=transaction_total(db, user_id, "income", month, year, day),
            expenses=transaction_total(db, user_id, "expense", month, year, day),
        ),
        monthly_spending=[MonthlySpendingPoint(month=item.month, expenses=item.expenses) for item in yearly_trends],
        monthly_trends=trends,
        top_merchants=merchant_rows,
    )


def build_merchant_analytics(
    db: Session,
    user_id: int,
    month: int,
    year: int,
    day: int | None = None,
) -> list[ChartDataPoint]:
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, Transaction.description, "Unknown merchant")
    rows = (
        db.query(merchant_name.label("name"), func.sum(Transaction.amount).label("value"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            *_period_filter(user_id, month, year, day),
            Transaction.transaction_type == "expense",
            func.lower(func.coalesce(Category.name, "")).notin_(SAVINGS_ALLOCATION_CATEGORY_NAMES),
        )
        .group_by(merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
        .all()
    )
    return [ChartDataPoint(name=row.name, value=round(float(row.value or 0), 2)) for row in rows]
