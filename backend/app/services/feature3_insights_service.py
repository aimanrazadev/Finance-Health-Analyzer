from datetime import datetime
from sqlalchemy.orm import Session
from app.ai.insights_llm_service import InsightsLLMService
from app.schemas.schemas import AIInsightsEngineResponse
from app.services.financial_context_service import build_financial_context
from app.services.prompt_builder_service import build_insights_prompt
from app.services.structured_insights_service import build_fallback_content,validate_llm_content

def build_ai_insights_engine_response(db:Session,user_id:int,month:int,year:int)->AIInsightsEngineResponse:
    context=build_financial_context(db,user_id,month,year);fallback=build_fallback_content(context);raw,provider=InsightsLLMService().generate(build_insights_prompt(context));content=validate_llm_content(raw) or fallback
    if content is fallback:provider='deterministic'
    change=context.trends.expense_change_percentage;trend='Steady' if change is None else 'Improving' if change<=0 else 'Needs attention'
    return AIInsightsEngineResponse(**content.model_dump(),month=month,year=year,provider=provider,generated_at=datetime.now(),context=context,health_score=context.health_score.overall_score,status=context.health_score.status,health_trend=trend)
