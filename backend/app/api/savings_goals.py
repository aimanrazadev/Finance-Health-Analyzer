from calendar import monthrange
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import SavingsGoal, User
from app.schemas.schemas import SavingsGoalCreate, SavingsGoalResponse, SavingsGoalUpdate

router = APIRouter(prefix="/savings-goals", tags=["savings goals"])


def add_months(start_date: datetime, months: int) -> datetime:
    """Add whole months without requiring an extra date library."""
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, monthrange(year, month)[1])
    return start_date.replace(year=year, month=month, day=day)


def build_goal_response(goal: SavingsGoal) -> SavingsGoalResponse:
    """Serialize a savings goal with progress, timeline, and practical suggestion."""
    current_amount = min(float(goal.current_amount or 0), float(goal.target_amount))
    remaining_amount = max(float(goal.target_amount) - current_amount, 0)
    monthly_contribution = float(goal.monthly_contribution or 0)
    progress_percentage = (current_amount / float(goal.target_amount) * 100) if goal.target_amount else 0
    months_required = ceil(remaining_amount / monthly_contribution) if monthly_contribution > 0 and remaining_amount > 0 else None
    estimated_completion_date = add_months(datetime.now(), months_required) if months_required else None

    if remaining_amount <= 0:
        suggestion = "Goal reached. Keep this money separate so it stays protected."
        resolved_status = "completed"
    elif monthly_contribution <= 0:
        suggestion = f"Start with a monthly contribution of INR {max(ceil(remaining_amount / 12), 500):,.0f} to build steady progress."
        resolved_status = goal.status
    else:
        target_months = max(1, ceil((goal.target_date - datetime.now()).days / 30))
        required_monthly = remaining_amount / target_months
        if monthly_contribution >= required_monthly:
            suggestion = "Current monthly contribution is enough to reach the target date."
        else:
            increase_by = required_monthly - monthly_contribution
            suggestion = f"Increase monthly contribution by about INR {increase_by:,.0f} to reach the target date faster."
        resolved_status = goal.status

    return SavingsGoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=current_amount,
        monthly_contribution=monthly_contribution,
        remaining_amount=round(remaining_amount, 2),
        progress_percentage=round(min(progress_percentage, 100), 2),
        months_required=months_required,
        estimated_completion_date=estimated_completion_date,
        ai_suggestion=suggestion,
        target_date=goal.target_date,
        created_at=goal.created_at,
        status=resolved_status,
    )


def get_goal_or_404(db: Session, user_id: int, goal_id: int) -> SavingsGoal:
    """Fetch a user-owned goal or raise a 404."""
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Savings goal not found")
    return goal


@router.post("/", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
def create_savings_goal(
    payload: SavingsGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a savings goal for the current user."""
    goal = SavingsGoal(
        user_id=current_user.id,
        name=payload.name.strip(),
        target_amount=payload.target_amount,
        current_amount=min(payload.current_amount, payload.target_amount),
        monthly_contribution=payload.monthly_contribution,
        target_date=payload.target_date,
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return build_goal_response(goal)


@router.get("/", response_model=list[SavingsGoalResponse])
def list_savings_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all savings goals for the current user."""
    goals = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.user_id == current_user.id)
        .order_by(SavingsGoal.created_at.desc())
        .all()
    )
    return [build_goal_response(goal) for goal in goals]


@router.put("/{goal_id}", response_model=SavingsGoalResponse)
def update_savings_goal(
    goal_id: int,
    payload: SavingsGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a user-owned savings goal."""
    goal = get_goal_or_404(db, current_user.id, goal_id)
    goal.name = payload.name.strip()
    goal.target_amount = payload.target_amount
    goal.current_amount = min(payload.current_amount, payload.target_amount)
    goal.monthly_contribution = payload.monthly_contribution
    goal.target_date = payload.target_date
    goal.status = payload.status
    db.commit()
    db.refresh(goal)
    return build_goal_response(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_savings_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a user-owned savings goal."""
    goal = get_goal_or_404(db, current_user.id, goal_id)
    db.delete(goal)
    db.commit()
    return None
