from sqlalchemy.orm import Session

from app.schemas.schemas import DashboardInsightItem, DashboardInsightsResponse
from app.services.dashboard_summary_service import build_dashboard_summary


def _change_percentage(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 1)


def _previous_period(month: int, year: int) -> tuple[int, int]:
    if month == -1:
        return -1, year
    if month == 0:
        return 0, year - 1
    if month == 1:
        return 12, year - 1
    return month - 1, year


def _severity_for_change(change: float) -> str:
    if change >= 15:
        return "warning"
    if change <= -10:
        return "positive"
    return "neutral"


def build_dashboard_insights(db: Session, user_id: int, month: int, year: int, day: int | None = None) -> DashboardInsightsResponse:
    current = build_dashboard_summary(db, user_id, month, year, day)
    previous_month, previous_year = _previous_period(month, year)
    previous = build_dashboard_summary(db, user_id, previous_month, previous_year)
    insights: list[DashboardInsightItem] = []

    expense_change = _change_percentage(current.total_expenses, previous.total_expenses)
    if expense_change is not None:
        direction = "increased" if expense_change >= 0 else "decreased"
        insights.append(DashboardInsightItem(
            title="Spending trend",
            message=f"Expenses {direction} {abs(expense_change):.1f}% compared with the previous period.",
            severity=_severity_for_change(expense_change),
        ))

    if current.top_category:
        category_total = current.category_breakdown[0].total if current.category_breakdown else 0
        insights.append(DashboardInsightItem(
            title="Top category",
            message=f"{current.top_category} is your highest spending category at INR {category_total:,.0f}.",
            severity="warning" if current.total_income and category_total / current.total_income >= 0.25 else "neutral",
        ))

    if current.top_merchant:
        insights.append(DashboardInsightItem(
            title="Top merchant",
            message=f"{current.top_merchant} is your highest spending merchant this period.",
            severity="neutral",
        ))

    if current.savings_rate >= 30:
        savings_message = f"You saved {current.savings_rate:.1f}% of your income, which is strong."
        savings_severity = "positive"
    elif current.savings_rate >= 10:
        savings_message = f"You saved {current.savings_rate:.1f}% of your income. There is room to improve."
        savings_severity = "neutral"
    else:
        savings_message = f"Your savings rate is {current.savings_rate:.1f}%, so savings need attention."
        savings_severity = "warning"
    insights.append(DashboardInsightItem(
        title="Savings status",
        message=savings_message,
        severity=savings_severity,
    ))

    if current.recurring_subscription_count:
        insights.append(DashboardInsightItem(
            title="Subscriptions",
            message=(
                f"{current.recurring_subscription_count} recurring subscriptions detected "
                f"with INR {current.recurring_subscription_total:,.0f} monthly total."
            ),
            severity="warning" if current.recurring_subscription_total > current.total_income * 0.1 else "neutral",
        ))

    if current.category_breakdown and current.total_expenses:
        high_categories = [
            item.category_name
            for item in current.category_breakdown
            if item.total / current.total_expenses >= 0.30
        ]
        if high_categories:
            insights.append(DashboardInsightItem(
                title="High concentration",
                message=f"{', '.join(high_categories[:2])} takes a large share of your spending.",
                severity="warning",
            ))

    if current.financial_health_reason and len(insights) < 5:
        insights.append(DashboardInsightItem(
            title="Health score",
            message=f"{current.financial_health_status}: {current.financial_health_reason}",
            severity="positive" if current.financial_health_score >= 80 else "warning" if current.financial_health_score < 50 else "neutral",
        ))

    if current.transaction_count == 0:
        insights.append(DashboardInsightItem(
            title="No activity yet",
            message="Add or upload transactions to generate smart dashboard insights.",
            severity="neutral",
        ))

    while len(insights) < 3:
        insights.append(DashboardInsightItem(
            title="More history needed",
            message="Add more categorized transactions to unlock stronger month-to-month insights.",
            severity="neutral",
        ))

    return DashboardInsightsResponse(month=month, year=year, insights=insights[:5])
