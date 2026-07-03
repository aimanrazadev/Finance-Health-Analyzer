from calendar import monthrange
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.schemas import FinancialSnapshotResponse
from app.analytics.analytics import build_dashboard_summary


def build_financial_snapshot(db: Session, user_id: int, month: int, year: int) -> FinancialSnapshotResponse:
    """Project the current month forward and create proactive dashboard alerts."""
    summary = build_dashboard_summary(db, user_id, month, year)
    today = date.today()
    days_in_month = monthrange(year, month)[1]
    elapsed_days = today.day if today.month == month and today.year == year else days_in_month
    pace_factor = days_in_month / max(elapsed_days, 1)

    lifestyle_spending = sum(item.total for item in summary.category_breakdown)
    projected_spending = round(lifestyle_spending * pace_factor, 2)
    projected_savings = round(summary.total_savings * pace_factor, 2)
    projected_savings_rate = round((projected_savings / summary.available_funds * 100), 2) if summary.available_funds else None

    if projected_savings_rate is None:
        budget_health = "N/A"
    elif projected_savings_rate >= 25:
        budget_health = "Good"
    elif projected_savings_rate >= 10:
        budget_health = "Average"
    else:
        budget_health = "Needs Attention"

    alerts: list[str] = []
    if projected_spending > summary.total_expenses and elapsed_days < days_in_month:
        alerts.append(f"At this pace, spending may reach INR {projected_spending:,.0f} by month end.")
    if summary.top_category:
        alerts.append(f"{summary.top_category} is currently your top spending category.")
    if summary.top_merchant:
        alerts.append(f"{summary.top_merchant} is currently your top spending merchant.")
    if summary.total_savings == 0 and summary.total_income > 0:
        alerts.append("No transactions are categorized as Savings or Investments this month.")

    return FinancialSnapshotResponse(
        month=month,
        year=year,
        current_month_spending=round(lifestyle_spending, 2),
        projected_month_end_spending=projected_spending,
        projected_month_end_savings=projected_savings,
        projected_savings_rate=projected_savings_rate,
        budget_health=budget_health,
        top_merchant=summary.top_merchant,
        top_category=summary.top_category,
        alerts=alerts[:4],
    )
