from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    CategoryAnalyticsResponse,
    CategoryMerchantBreakdownResponse,
    ChartDataPoint,
    DashboardDataResponse,
    DashboardChartsResponse,
    DashboardInsightsResponse,
    DashboardSummary,
    FinancialSnapshotResponse,
    IncomeExpenseChart,
    MerchantAnalyticsResponse,
    MonthlySpendingPoint,
    MonthlyTrendResponse,
    SavingsAnalyticsResponse,
    SubscriptionAnalyticsResponse,
)
from app.services.dashboard_insights_service import build_dashboard_insights
from app.services.analytics_service import (
    build_dashboard_charts,
    build_dashboard_summary,
    build_merchant_analytics,
    build_monthly_trends,
)
from app.services.financial_analytics_service import (
    build_category_analytics,
    build_category_merchant_breakdown,
    build_complete_dashboard_data,
    build_merchant_analytics_detail,
    build_savings_analytics,
    build_subscription_analytics,
)
from app.services.financial_health_service import calculate_financial_health_score
from app.services.financial_snapshot_service import build_financial_snapshot

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def resolve_period(month: Optional[int], year: Optional[int], day: Optional[int] = None) -> tuple[int, int, Optional[int]]:
    today = date.today()
    selected_month = today.month if month is None else month
    selected_year = year or today.year

    if selected_month < -1 or selected_month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be between -1 and 12")
    if selected_year < 2000 or selected_year > 2100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="year must be between 2000 and 2100")
    if day is not None:
        if selected_month <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="day requires a selected month")
        try:
            date(selected_year, selected_month, day)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid day for selected month") from exc
    return selected_month, selected_year, day


@router.get("", response_model=DashboardDataResponse)
def get_complete_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_complete_dashboard_data(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_dashboard_summary(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/savings", response_model=SavingsAnalyticsResponse)
def get_savings_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_savings_analytics(db, current_user.id, selected_month, selected_year)


@router.get("/categories", response_model=CategoryAnalyticsResponse)
def get_category_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_category_analytics(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/category-merchants", response_model=CategoryMerchantBreakdownResponse)
def get_category_merchant_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_category_merchant_breakdown(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/merchants", response_model=MerchantAnalyticsResponse)
def get_merchant_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_merchant_analytics_detail(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/subscriptions", response_model=SubscriptionAnalyticsResponse)
def get_subscription_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_subscription_analytics(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/health-score")
def get_dashboard_health_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year, _selected_day = resolve_period(month, year)
    if selected_month == 0:
        selected_month = date.today().month
    return calculate_financial_health_score(db, current_user.id, selected_month, selected_year)


@router.get("/insights", response_model=DashboardInsightsResponse)
def get_dashboard_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_dashboard_insights(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/snapshot", response_model=FinancialSnapshotResponse)
def get_financial_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year, _selected_day = resolve_period(month, year)
    if selected_month == 0:
        selected_month = date.today().month
    return build_financial_snapshot(db, current_user.id, selected_month, selected_year)


@router.get("/charts", response_model=DashboardChartsResponse)
def get_dashboard_charts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/charts/category-breakdown", response_model=list[ChartDataPoint])
def get_category_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year, selected_day).category_breakdown


@router.get("/charts/income-vs-expense", response_model=IncomeExpenseChart)
def get_income_expense_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year, selected_day).income_vs_expense


@router.get("/charts/monthly-spending", response_model=list[MonthlySpendingPoint])
def get_monthly_spending_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    year: Optional[int] = None,
):
    _selected_month, selected_year, _selected_day = resolve_period(0, year)
    return build_dashboard_charts(db, current_user.id, 0, selected_year).monthly_spending


@router.get("/charts/monthly-trends", response_model=MonthlyTrendResponse)
def get_monthly_trends_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    year: Optional[int] = None,
):
    _selected_month, selected_year, _selected_day = resolve_period(0, year)
    return build_monthly_trends(db, current_user.id, selected_year)


@router.get("/charts/top-merchants", response_model=list[ChartDataPoint])
def get_top_merchants_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_merchant_analytics(db, current_user.id, selected_month, selected_year, selected_day)


@router.get("/charts/merchant-analytics", response_model=list[ChartDataPoint])
def get_merchant_analytics_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
):
    selected_month, selected_year, selected_day = resolve_period(month, year, day)
    return build_merchant_analytics(db, current_user.id, selected_month, selected_year, selected_day)
