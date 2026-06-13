from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import ExpenseForecastResponse
from app.services.expense_forecast_service import generate_expense_forecast

router = APIRouter(prefix="/forecast", tags=["expense forecasting"])


@router.get("/expenses", response_model=ExpenseForecastResponse)
def get_expense_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Predict next-month total and category-wise expenses for the current user."""
    return generate_expense_forecast(db, current_user.id)
