from fastapi import APIRouter,Depends,Query,Response
from sqlalchemy.orm import Session
from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import AIInsightsEngineResponse
from app.services.feature3_insights_service import build_ai_insights_engine_response
router=APIRouter(prefix="/ai",tags=["ai insights"])

@router.get("/insights",response_model=AIInsightsEngineResponse)
def get_ai_insights(response:Response,month:int=Query(ge=1,le=12),year:int=Query(ge=2000,le=2100),current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    response.headers["Cache-Control"]="no-store, no-cache, must-revalidate"
    response.headers["Pragma"]="no-cache"
    return build_ai_insights_engine_response(db,current_user.id,month,year)
