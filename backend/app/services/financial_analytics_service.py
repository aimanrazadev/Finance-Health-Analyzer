from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Category, Subscription, Transaction
from app.schemas.schemas import (
    CategoryAnalyticsItem,
    CategoryAnalyticsResponse,
    CategoryMerchantBreakdownItem,
    CategoryMerchantBreakdownResponse,
    CategoryMerchantItem,
    DashboardDataResponse,
    DashboardRecentTransaction,
    MerchantAnalyticsItem,
    MerchantAnalyticsResponse,
    SavingsAnalyticsResponse,
    SubscriptionAnalyticsItem,
    SubscriptionAnalyticsResponse,
)
from app.services.dashboard_insights_service import build_dashboard_insights
from app.services.analytics_service import (
    SAVINGS_ALLOCATION_CATEGORY_NAMES,
    SUBSCRIPTION_CATEGORY_NAMES,
    build_dashboard_charts,
    build_dashboard_summary,
    build_monthly_trends,
    build_period_trend_summary,
    period_bounds as month_bounds,
    previous_period,
)


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
            func.lower(func.coalesce(Category.name, "")).notin_(SAVINGS_ALLOCATION_CATEGORY_NAMES),
        )
        .group_by(Transaction.category_id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    total_expenses = round(sum(float(row.total or 0) for row in rows), 2)
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

    return CategoryAnalyticsResponse(
        month=month,
        year=year,
        total_expenses=total_expenses,
        highest_spending_category=items[0].category_name if items else None,
        categories=items,
    )


def build_category_merchant_breakdown(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> CategoryMerchantBreakdownResponse:
    """Group expense spending by category, then by merchant within each category."""
    start_date, end_date = month_bounds(month, year, day)
    merchant_name = func.coalesce(Transaction.extracted_merchant, Transaction.merchant, Transaction.description, "Unknown merchant")
    rows = (
        db.query(
            Transaction.category_id.label("category_id"),
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            Category.color.label("color"),
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
            func.lower(func.coalesce(Category.name, "")).notin_(SAVINGS_ALLOCATION_CATEGORY_NAMES),
        )
        .group_by(Transaction.category_id, Category.name, Category.color, merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    category_map: dict[tuple[int | None, str], dict] = {}
    for row in rows:
        key = (row.category_id, row.category_name)
        if key not in category_map:
            category_map[key] = {
                "category_id": row.category_id,
                "category_name": row.category_name,
                "color": row.color,
                "total": 0.0,
                "transaction_count": 0,
                "merchants": [],
            }
        category = category_map[key]
        merchant_total = round(float(row.total_spent or 0), 2)
        merchant_count = int(row.transaction_count or 0)
        category["total"] += merchant_total
        category["transaction_count"] += merchant_count
        category["merchants"].append({
            "merchant_name": row.merchant_name or "Unknown merchant",
            "total_spent": merchant_total,
            "transaction_count": merchant_count,
        })

    total_expenses = round(sum(category["total"] for category in category_map.values()), 2)
    categories = []
    for category in sorted(category_map.values(), key=lambda item: item["total"], reverse=True):
        category_total = round(category["total"], 2)
        merchants = [
            CategoryMerchantItem(
                merchant_name=merchant["merchant_name"],
                total_spent=merchant["total_spent"],
                transaction_count=merchant["transaction_count"],
                percentage=round((merchant["total_spent"] / category_total * 100), 2) if category_total else 0,
            )
            for merchant in sorted(category["merchants"], key=lambda item: item["total_spent"], reverse=True)[:8]
        ]
        categories.append(
            CategoryMerchantBreakdownItem(
                category_id=category["category_id"],
                category_name=category["category_name"],
                total=category_total,
                percentage=round((category_total / total_expenses * 100), 2) if total_expenses else 0,
                transaction_count=category["transaction_count"],
                color=category["color"],
                merchants=merchants,
            )
        )

    return CategoryMerchantBreakdownResponse(
        month=month,
        year=year,
        total_expenses=total_expenses,
        categories=categories,
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
            func.lower(func.coalesce(Category.name, "")).notin_(SAVINGS_ALLOCATION_CATEGORY_NAMES),
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
                annual_cost=round(average_amount * 12, 2),
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
        total_annual_cost=round(sum(item.annual_cost for item in items), 2),
        subscriptions=items,
    )


def build_complete_dashboard_data(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> DashboardDataResponse:
    """Build one complete payload for the React dashboard."""
    from app.services.financial_health_service import calculate_financial_health_score

    start_date, end_date = month_bounds(month, year, day)
    recent_rows = (
        db.query(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == user_id, Transaction.date >= start_date, Transaction.date <= end_date)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(8)
        .all()
    )
    recent_transactions = [
        DashboardRecentTransaction(
            id=transaction.id,
            date=transaction.date,
            description=transaction.description,
            merchant=transaction.extracted_merchant or transaction.merchant,
            category_name=category.name if category else "Uncategorized",
            transaction_type=transaction.transaction_type,
            amount=round(float(transaction.amount or 0), 2),
            closing_balance=transaction.balance,
        )
        for transaction, category in recent_rows
    ]
    return DashboardDataResponse(
        summary=build_dashboard_summary(db, user_id, month, year, day),
        savings=build_savings_analytics(db, user_id, month, year),
        categories=build_category_analytics(db, user_id, month, year, day),
        merchants=build_merchant_analytics_detail(db, user_id, month, year, day),
        subscriptions=build_subscription_analytics(db, user_id, month, year, day),
        charts=build_dashboard_charts(db, user_id, month, year, day),
        trends=build_period_trend_summary(db, user_id, month, year, day),
        insights=build_dashboard_insights(db, user_id, month, year, day),
        health=calculate_financial_health_score(db, user_id, month, year),
        recent_transactions=recent_transactions,
    )
