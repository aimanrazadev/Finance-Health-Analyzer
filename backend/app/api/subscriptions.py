from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import SubscriptionsResponse
from app.services.subscription_service import list_active_subscriptions

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/", response_model=SubscriptionsResponse)
def get_subscriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Detect and return active recurring payments for the current user."""
    return list_active_subscriptions(db, current_user.id)


@router.post("/refresh", response_model=SubscriptionsResponse)
def refresh_subscriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Refresh recurring payment detection and mark matching transactions as recurring."""
    return list_active_subscriptions(db, current_user.id)
