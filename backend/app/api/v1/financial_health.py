from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import FinancialHealthScoreResponse
from app.analytics.financial_health import calculate_financial_health_score

router = APIRouter(prefix="/financial-health", tags=["financial health"])


@router.get("/score", response_model=FinancialHealthScoreResponse)
def get_financial_health_score(
    month: int | None = Query(default=None),
    year: int | None = Query(default=None, ge=2000, le=2100),
    day: int | None = Query(default=None, ge=1, le=31),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate and store the current user's financial health score."""
    today = datetime.now()
    selected_month = month if month is not None else today.month
    if selected_month < -1 or selected_month > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must be -1 (all time), 0 (full year), or 1 through 12",
        )
    if day is not None:
        if selected_month <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="day requires a selected month")
        try:
            datetime(year or today.year, selected_month, day)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid day for selected month") from exc
    return calculate_financial_health_score(
        db,
        current_user.id,
        selected_month,
        year or today.year,
        day,
    )
