from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import AIInsightsEngineResponse
from app.services.feature3_insights_service import build_ai_insights_engine_response
router=APIRouter(prefix="/ai",tags=["ai insights"])

@router.get("/insights",response_model=AIInsightsEngineResponse)
def get_ai_insights(month:int,year:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return build_ai_insights_engine_response(db,current_user.id,month,year)
