from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    BudgetUsageChartItem,
    ChartDataPoint,
    DashboardChartsResponse,
    DashboardSummary,
    IncomeExpenseChart,
    MonthlySpendingPoint,
    SuggestedBudgetResponse,
)
from app.services.dashboard_summary_service import (
    build_budget_usage_chart,
    build_dashboard_charts,
    build_dashboard_summary,
    build_merchant_analytics,
    build_subscription_chart,
    generate_suggested_budgets,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def resolve_period(month: Optional[int], year: Optional[int]) -> tuple[int, int]:
    today = date.today()
    selected_month = today.month if month is None else month
    selected_year = year or today.year

    if selected_month < 0 or selected_month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be between 0 and 12")
    if selected_year < 2000 or selected_year > 2100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="year must be between 2000 and 2100")
    return selected_month, selected_year


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_dashboard_summary(db, current_user.id, selected_month, selected_year)


@router.get("/charts", response_model=DashboardChartsResponse)
def get_dashboard_charts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year)


@router.get("/charts/category-breakdown", response_model=list[ChartDataPoint])
def get_category_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year).category_breakdown


@router.get("/charts/income-vs-expense", response_model=IncomeExpenseChart)
def get_income_expense_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year).income_vs_expense


@router.get("/charts/monthly-spending", response_model=list[MonthlySpendingPoint])
def get_monthly_spending_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    year: Optional[int] = None,
):
    _selected_month, selected_year = resolve_period(0, year)
    return build_dashboard_charts(db, current_user.id, 0, selected_year).monthly_spending


@router.get("/charts/top-merchants", response_model=list[ChartDataPoint])
def get_top_merchants_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_merchant_analytics(db, current_user.id, selected_month, selected_year)


@router.get("/charts/merchant-analytics", response_model=list[ChartDataPoint])
def get_merchant_analytics_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_merchant_analytics(db, current_user.id, selected_month, selected_year)


@router.get("/charts/budget-usage", response_model=list[BudgetUsageChartItem])
def get_budget_usage_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_budget_usage_chart(db, current_user.id, selected_month, selected_year)


@router.get("/charts/subscriptions", response_model=list[ChartDataPoint])
def get_subscription_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_subscription_chart(db, current_user.id)


@router.get("/budget-suggestions", response_model=list[SuggestedBudgetResponse])
def get_budget_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return generate_suggested_budgets(db, current_user.id, selected_month, selected_year, store=False)


@router.post("/budget-suggestions/generate", response_model=list[SuggestedBudgetResponse])
def store_budget_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return generate_suggested_budgets(db, current_user.id, selected_month, selected_year, store=True)
