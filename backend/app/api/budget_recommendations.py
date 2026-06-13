from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import BudgetRecommendationsResponse
from app.services.budget_recommendation_service import generate_budget_recommendations

router = APIRouter(prefix="/budget-recommendations", tags=["budget recommendations"])


@router.get("/", response_model=BudgetRecommendationsResponse)
def get_budget_recommendations(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return ranked budget recommendations for the selected month."""
    today = datetime.now()
    return generate_budget_recommendations(
        db,
        current_user.id,
        month or today.month,
        year or today.year,
    )
