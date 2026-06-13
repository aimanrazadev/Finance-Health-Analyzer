from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Budget, Category, Transaction, User
from app.schemas.schemas import BudgetCreate, BudgetResponse, BudgetUpdate

router = APIRouter(prefix="/budgets", tags=["budgets"])

SMART_BUDGET_MILESTONES = [50, 75, 90, 95, 99]


def ensure_category_exists(db: Session, category_id: int) -> Category:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected category does not exist",
        )
    return category


def budget_period(month: int, year: int) -> str:
    return f"{year:04d}-{month:02d}"


def parse_budget_period(period: str) -> tuple[int, int]:
    try:
        year_text, month_text = period.split("-")
        return int(month_text), int(year_text)
    except ValueError:
        today = date.today()
        return today.month, today.year


def calculate_actual_spent(db: Session, user_id: int, category_id: int, month: int, year: int) -> float:
    total = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.transaction_type == "expense",
            func.month(Transaction.date) == month,
            func.year(Transaction.date) == year,
        )
        .scalar()
    )
    return float(total or 0)


def serialize_budget(db: Session, budget: Budget) -> BudgetResponse:
    month, year = parse_budget_period(budget.period)
    actual_spent = calculate_actual_spent(db, budget.user_id, budget.category_id, month, year)
    remaining_amount = budget.amount - actual_spent
    percentage_used = (actual_spent / budget.amount * 100) if budget.amount else 0

    reached_milestones = [milestone for milestone in SMART_BUDGET_MILESTONES if percentage_used >= milestone]
    next_milestone = next((milestone for milestone in SMART_BUDGET_MILESTONES if percentage_used < milestone), None)

    if actual_spent > budget.amount:
        budget_status = "over_budget"
        alert_message = f"Over budget by {abs(remaining_amount):.2f}."
    elif percentage_used >= 99:
        budget_status = "critical"
        alert_message = "99% budget milestone reached. Treat this category as fully used."
    elif percentage_used >= 95:
        budget_status = "critical"
        alert_message = "95% budget milestone reached. Very little room is left."
    elif percentage_used >= 90:
        budget_status = "warning"
        alert_message = "90% budget milestone reached. Slow spending in this category."
    elif percentage_used >= 75:
        budget_status = "watch"
        alert_message = "75% budget milestone reached. Keep an eye on this category."
    elif percentage_used >= 50:
        budget_status = "half_used"
        alert_message = "50% budget milestone reached."
    else:
        budget_status = "on_track"
        alert_message = f"Next smart milestone: {next_milestone}%." if next_milestone else None

    category = db.query(Category).filter(Category.id == budget.category_id).first()

    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        category_name=category.name if category else None,
        monthly_limit=float(budget.amount),
        month=month,
        year=year,
        alert_threshold=0,
        smart_milestones=SMART_BUDGET_MILESTONES,
        reached_milestones=reached_milestones,
        next_milestone=next_milestone,
        actual_spent=round(actual_spent, 2),
        remaining_amount=round(remaining_amount, 2),
        percentage_used=round(percentage_used, 2),
        status=budget_status,
        alert_message=alert_message,
        created_at=budget.created_at,
        is_active=budget.is_active,
    )


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_category_exists(db, budget_data.category_id)

    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.category_id == budget_data.category_id,
            Budget.period == budget_period(budget_data.month, budget_data.year),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A budget already exists for this category and month.",
        )

    budget = Budget(
        user_id=current_user.id,
        category_id=budget_data.category_id,
        amount=budget_data.monthly_limit,
        period=budget_period(budget_data.month, budget_data.year),
        alert_threshold=0,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return serialize_budget(db, budget)


@router.get("/", response_model=List[BudgetResponse])
def get_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: int | None = None,
    year: int | None = None,
):
    query = db.query(Budget).filter(Budget.user_id == current_user.id)
    if month and year:
        query = query.filter(Budget.period == budget_period(month, year))
    elif year:
        query = query.filter(Budget.period.like(f"{year:04d}-%"))

    budgets = query.order_by(Budget.created_at.desc()).all()
    return [serialize_budget(db, budget) for budget in budgets]


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    budget_data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    ensure_category_exists(db, budget_data.category_id)
    duplicate = (
        db.query(Budget)
        .filter(
            Budget.id != budget_id,
            Budget.user_id == current_user.id,
            Budget.category_id == budget_data.category_id,
            Budget.period == budget_period(budget_data.month, budget_data.year),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Another budget already exists for this category and month.",
        )

    budget.category_id = budget_data.category_id
    budget.amount = budget_data.monthly_limit
    budget.period = budget_period(budget_data.month, budget_data.year)
    budget.alert_threshold = 0
    budget.is_active = budget_data.is_active
    db.commit()
    db.refresh(budget)
    return serialize_budget(db, budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    db.delete(budget)
    db.commit()
