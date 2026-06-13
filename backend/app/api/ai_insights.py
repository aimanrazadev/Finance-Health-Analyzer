from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import AiInsightsResponse
from app.services.spending_insights import generate_and_store_insights

router = APIRouter(prefix="/ai", tags=["ai insights"])


@router.get("/insights", response_model=AiInsightsResponse)
def get_ai_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None,
    regenerate: bool = False,
):
    today = date.today()
    selected_month = month or today.month
    selected_year = year or today.year

    insights = generate_and_store_insights(
        db,
        current_user.id,
        selected_month,
        selected_year,
        regenerate=regenerate,
    )

    return AiInsightsResponse(
        month=selected_month,
        year=selected_year,
        insights=insights,
    )
