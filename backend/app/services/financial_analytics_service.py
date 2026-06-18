from calendar import monthrange
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Category, Subscription, Transaction
from app.schemas.schemas import (
    CategoryAnalyticsItem,
    CategoryAnalyticsResponse,
    DashboardDataResponse,
    MerchantAnalyticsItem,
    MerchantAnalyticsResponse,
    SavingsAnalyticsResponse,
    SubscriptionAnalyticsItem,
    SubscriptionAnalyticsResponse,
)
from app.services.dashboard_insights_service import build_dashboard_insights
from app.services.dashboard_summary_service import (
    INVESTMENT_CATEGORY_NAMES,
    SUBSCRIPTION_CATEGORY_NAMES,
    build_dashboard_charts,
    build_dashboard_summary,
)


def month_bounds(month: int, year: int, day: int | None = None) -> tuple[datetime, datetime]:
    if day and month > 0:
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


def build_savings_analytics(db: Session, user_id: int, month: int, year: int) -> SavingsAnalyticsResponse:
    """Measure how much income became savings and compare it with the prior period."""
    current = build_dashboard_summary(db, user_id, month, year)
    previous_month, previous_year = previous_period(month, year)
    previous = build_dashboard_summary(db, user_id, previous_month, previous_year)

    return SavingsAnalyticsResponse(
        month=month,
        year=year,
        savings=current.total_savings,
        savings_rate=current.savings_rate,
        monthly_savings_trend=current.monthly_savings_trend,
        previous_month_savings=previous.total_savings,
        savings_status=current.savings_status,
    )


def build_category_analytics(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> CategoryAnalyticsResponse:
    """Group expense transactions by category and calculate spending share."""
    start_date, end_date = month_bounds(month, year, day)
    rows = (
        db.query(
            Transaction.category_id,
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            Category.color.label("color"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .group_by(Transaction.category_id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    total_expenses = round(
        sum(float(row.total or 0) for row in rows if row.category_name.lower() not in INVESTMENT_CATEGORY_NAMES),
        2,
    )
    items = [
        CategoryAnalyticsItem(
            category_id=row.category_id,
            category_name=row.category_name,
            total=round(float(row.total or 0), 2),
            percentage=round((float(row.total or 0) / total_expenses * 100), 2) if total_expenses else 0,
            transaction_count=int(row.transaction_count or 0),
            color=row.color,
        )
        for row in rows
    ]

    non_investment_items = [
        item for item in items if item.category_name.lower() not in INVESTMENT_CATEGORY_NAMES
    ]
    return CategoryAnalyticsResponse(
        month=month,
        year=year,
        total_expenses=total_expenses,
        highest_spending_category=non_investment_items[0].category_name if non_investment_items else None,
        categories=items,
    )


def build_merchant_analytics_detail(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> MerchantAnalyticsResponse:
    """Group spending by merchant and expose both value and frequency views."""
    start_date, end_date = month_bounds(month, year, day)
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, "Unknown merchant")
    rows = (
        db.query(
            merchant_name.label("merchant_name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total_spent"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            func.lower(func.coalesce(Category.name, "")).notin_(INVESTMENT_CATEGORY_NAMES),
        )
        .group_by(merchant_name)
        .all()
    )

    items = [
        MerchantAnalyticsItem(
            merchant_name=row.merchant_name,
            total_spent=round(float(row.total_spent or 0), 2),
            transaction_count=int(row.transaction_count or 0),
            frequency=int(row.transaction_count or 0),
            average_amount=round(float(row.total_spent or 0) / int(row.transaction_count or 1), 2),
        )
        for row in rows
    ]
    by_spend = sorted(items, key=lambda item: item.total_spent, reverse=True)[:10]
    by_frequency = sorted(items, key=lambda item: item.frequency, reverse=True)[:10]
    return MerchantAnalyticsResponse(
        month=month,
        year=year,
        top_merchants=by_spend[:5],
        most_frequent_merchants=by_frequency,
        highest_spending_merchants=by_spend,
    )


def _upsert_subscription(
    db: Session,
    user_id: int,
    merchant_name: str,
    category_id: int | None,
    amount: float,
    confidence: float,
    next_expected_payment: datetime | None,
) -> Subscription:
    row = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.merchant_name == merchant_name,
            Subscription.status == "active",
        )
        .first()
    )
    if not row:
        row = Subscription(user_id=user_id, merchant_name=merchant_name)
        db.add(row)

    row.category_id = category_id
    row.amount = amount
    row.billing_period = "monthly"
    row.confidence = confidence
    row.next_expected_payment = next_expected_payment
    row.status = "active"
    return row


def build_subscription_analytics(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> SubscriptionAnalyticsResponse:
    """Detect recurring subscription load from Subscriptions-category transactions."""
    start_date, end_date = month_bounds(month, year, day)
    if month == -1:
        history_start = start_date
    else:
        history_start = datetime(end_date.year, max(1, end_date.month - 5), 1) if month != 0 else datetime(year, 1, 1)
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, Transaction.description)
    rows = (
        db.query(
            merchant_name.label("merchant_name"),
            Transaction.category_id.label("category_id"),
            func.coalesce(func.avg(Transaction.amount), 0).label("average_amount"),
            func.coalesce(func.sum(Transaction.amount), 0).label("period_total"),
            func.count(Transaction.id).label("transaction_count"),
            func.max(Transaction.date).label("last_payment_date"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= history_start,
            Transaction.date <= end_date,
            func.lower(Category.name).in_(SUBSCRIPTION_CATEGORY_NAMES),
        )
        .group_by(merchant_name, Transaction.category_id)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    items: list[SubscriptionAnalyticsItem] = []
    for row in rows:
        average_amount = round(float(row.average_amount or 0), 2)
        confidence = 0.95 if int(row.transaction_count or 0) >= 2 else 0.75
        next_expected_payment = row.last_payment_date + timedelta(days=30) if row.last_payment_date else None
        stored = _upsert_subscription(
            db,
            user_id,
            row.merchant_name,
            row.category_id,
            average_amount,
            confidence,
            next_expected_payment,
        )
        items.append(
            SubscriptionAnalyticsItem(
                id=stored.id,
                merchant_name=row.merchant_name,
                amount=average_amount,
                billing_period="monthly",
                monthly_cost=average_amount,
                transaction_count=int(row.transaction_count or 0),
                confidence=confidence,
                next_expected_payment=next_expected_payment,
            )
        )

    if items:
        db.commit()

    return SubscriptionAnalyticsResponse(
        month=month,
        year=year,
        subscription_count=len(items),
        total_monthly_cost=round(sum(item.monthly_cost for item in items), 2),
        subscriptions=items,
    )


def build_complete_dashboard_data(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> DashboardDataResponse:
    """Build one complete payload for the React dashboard."""
    return DashboardDataResponse(
        summary=build_dashboard_summary(db, user_id, month, year, day),
        savings=build_savings_analytics(db, user_id, month, year),
        categories=build_category_analytics(db, user_id, month, year, day),
        merchants=build_merchant_analytics_detail(db, user_id, month, year, day),
        subscriptions=build_subscription_analytics(db, user_id, month, year, day),
        charts=build_dashboard_charts(db, user_id, month, year, day),
        insights=build_dashboard_insights(db, user_id, month, year, day),
    )
