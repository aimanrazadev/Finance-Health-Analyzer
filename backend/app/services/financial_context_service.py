from calendar import month_name

from sqlalchemy.orm import Session

from app.schemas.schemas import (
    AICategoryContext,
    AICoreMetrics,
    AIFinancialContext,
    AIHealthComponents,
    AIHealthContext,
    AIMerchantContext,
    AISubscriptionContext,
    AITrendContext,
)
from app.services.analytics_service import build_dashboard_summary, build_period_trend_summary
from app.services.financial_analytics_service import (
    build_category_analytics,
    build_merchant_analytics_detail,
    build_subscription_analytics,
)
from app.services.financial_health_service import calculate_financial_health_score


def build_financial_context(db: Session, user_id: int, month: int, year: int) -> AIFinancialContext:
    """Collect verified Feature 2 outputs without reimplementing its finance math."""
    summary = build_dashboard_summary(db, user_id, month, year)
    categories = build_category_analytics(db, user_id, month, year)
    merchants = build_merchant_analytics_detail(db, user_id, month, year)
    subscriptions = build_subscription_analytics(db, user_id, month, year)
    trends = build_period_trend_summary(db, user_id, month, year)
    health = calculate_financial_health_score(db, user_id, month, year)

    subscription_share = None
    if summary.total_income > 0:
        subscription_share = round(subscriptions.total_monthly_cost / summary.total_income * 100, 2)

    return AIFinancialContext(
        period_label=f"{month_name[month]} {year}",
        month=month,
        year=year,
        transaction_count=summary.transaction_count,
        core_metrics=AICoreMetrics(
            opening_balance=summary.opening_balance,
            total_income=summary.total_income,
            total_expenses=summary.total_expenses,
            total_savings=summary.total_savings,
            lifestyle_expenses=summary.lifestyle_expenses,
            available_funds=summary.available_funds,
            savings_rate=summary.savings_rate,
            actual_closing_balance=summary.closing_balance,
            expected_closing_balance=summary.expected_closing_balance,
            balance_difference=summary.balance_difference,
            balance_mismatch=summary.balance_mismatch,
        ),
        health_score=AIHealthContext(
            overall_score=health["overall_score"],
            status=health["status_label"],
            components=AIHealthComponents(
                savings_score=health["savings_score"],
                subscription_score=health["subscription_score"],
                spending_stability_score=health["stability_score"],
                financial_balance_score=health["balance_score"],
            ),
        ),
        top_categories=[
            AICategoryContext(name=item.category_name, total=item.total, percentage=item.percentage)
            for item in categories.categories[:5]
        ],
        top_merchants=[
            AIMerchantContext(
                name=item.merchant_name,
                total=item.total_spent,
                transaction_count=item.transaction_count,
            )
            for item in merchants.highest_spending_merchants[:5]
        ],
        subscriptions=AISubscriptionContext(
            count=subscriptions.subscription_count,
            monthly_total=subscriptions.total_monthly_cost,
            share_of_income=subscription_share,
        ),
        trends=AITrendContext(
            income_change_percentage=trends.income_change_percentage,
            expense_change_percentage=trends.expense_change_percentage,
            savings_change_percentage=trends.savings_change_percentage,
        ),
    )
