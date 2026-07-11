from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import FinancialHealthScoreResponse
from app.analytics.financial_health import calculate_financial_health_score

router = APIRouter(prefix="/financial-health", tags=["financial health"])


@router.get("/score", response_model=FinancialHealthScoreResponse)
def get_financial_health_score(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate and store the current user's financial health score."""
    today = datetime.now()
    return calculate_financial_health_score(
        db,
        current_user.id,
        month or today.month,
        year or today.year,
    )
