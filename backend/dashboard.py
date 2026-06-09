from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Category, Transaction, User
from schemas import (
    CategoryBreakdownItem,
    ChartDataPoint,
    DashboardChartsResponse,
    DashboardSummary,
    IncomeExpenseChart,
    MonthlySpendingPoint,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def resolve_period(month: Optional[int], year: Optional[int]) -> tuple[int, int]:
    today = date.today()
    selected_month = month or today.month
    selected_year = year or today.year

    if selected_month < 1 or selected_month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month must be between 1 and 12",
        )

    if selected_year < 2000 or selected_year > 2100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="year must be between 2000 and 2100",
        )

    return selected_month, selected_year


def period_filter(query, selected_month: int, selected_year: int):
    return query.filter(
        func.month(Transaction.date) == selected_month,
        func.year(Transaction.date) == selected_year,
    )


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)

    base_query = period_filter(
        db.query(Transaction).filter(Transaction.user_id == current_user.id),
        selected_month,
        selected_year,
    )

    total_income = (
        base_query
        .filter(Transaction.transaction_type == "income")
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0))
        .scalar()
    )
    total_expenses = (
        base_query
        .filter(Transaction.transaction_type == "expense")
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0))
        .scalar()
    )
    total_savings = total_income - total_expenses
    savings_rate = (total_savings / total_income * 100) if total_income else 0

    category_rows = (
        db.query(
            Transaction.category_id,
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == selected_month,
            func.year(Transaction.date) == selected_year,
        )
        .group_by(Transaction.category_id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    category_breakdown = [
        CategoryBreakdownItem(
            category_id=row.category_id,
            category_name=row.category_name,
            total=float(row.total or 0),
        )
        for row in category_rows
    ]

    return DashboardSummary(
        month=selected_month,
        year=selected_year,
        total_income=float(total_income),
        total_expenses=float(total_expenses),
        total_savings=float(total_savings),
        savings_rate=round(savings_rate, 2),
        transaction_count=base_query.count(),
        top_category=category_breakdown[0].category_name if category_breakdown else None,
        category_breakdown=category_breakdown,
    )


def build_dashboard_charts(
    db: Session,
    user_id: int,
    selected_month: int,
    selected_year: int,
) -> DashboardChartsResponse:
    category_rows = (
        db.query(
            func.coalesce(Category.name, "Uncategorized").label("name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("value"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == selected_month,
            func.year(Transaction.date) == selected_year,
        )
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    total_income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
            func.month(Transaction.date) == selected_month,
            func.year(Transaction.date) == selected_year,
        )
        .scalar()
    )
    total_expenses = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == selected_month,
            func.year(Transaction.date) == selected_year,
        )
        .scalar()
    )

    monthly_rows = (
        db.query(
            func.month(Transaction.date).label("month_number"),
            func.coalesce(func.sum(Transaction.amount), 0).label("expenses"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            func.year(Transaction.date) == selected_year,
        )
        .group_by(func.month(Transaction.date))
        .order_by(func.month(Transaction.date))
        .all()
    )
    monthly_by_number = {
        int(row.month_number): float(row.expenses or 0)
        for row in monthly_rows
    }

    merchant_rows = (
        db.query(
            func.coalesce(Transaction.merchant, "Unknown merchant").label("name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("value"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == selected_month,
            func.year(Transaction.date) == selected_year,
        )
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
        .all()
    )

    return DashboardChartsResponse(
        month=selected_month,
        year=selected_year,
        category_breakdown=[
            ChartDataPoint(name=row.name, value=float(row.value or 0))
            for row in category_rows
        ],
        income_vs_expense=IncomeExpenseChart(
            income=float(total_income or 0),
            expenses=float(total_expenses or 0),
        ),
        monthly_spending=[
            MonthlySpendingPoint(month=date(selected_year, month_number, 1).strftime("%b"), expenses=monthly_by_number.get(month_number, 0))
            for month_number in range(1, 13)
        ],
        top_merchants=[
            ChartDataPoint(name=row.name, value=float(row.value or 0))
            for row in merchant_rows
        ],
    )


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
    selected_month, selected_year = resolve_period(None, year)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year).monthly_spending


@router.get("/charts/top-merchants", response_model=list[ChartDataPoint])
def get_top_merchants_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    selected_month, selected_year = resolve_period(month, year)
    return build_dashboard_charts(db, current_user.id, selected_month, selected_year).top_merchants
