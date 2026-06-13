from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import ChatHistory, User
from app.schemas.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConfirmRequest,
    AssistantConfirmResponse,
    AssistantHistoryResponse,
)
from app.services.assistant_agent_service import execute_confirmed_action, run_assistant

router = APIRouter(prefix="/assistant", tags=["ai financial assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat_with_assistant(
    payload: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run a user message through safe assistant tools and store chat history."""
    result = run_assistant(db, current_user.id, payload.message)
    history = ChatHistory(
        user_id=current_user.id,
        user_message=payload.message,
        assistant_response=result["message"],
        intent=result["intent"],
    )
    db.add(history)
    db.commit()
    return result


@router.post("/confirm", response_model=AssistantConfirmResponse)
def confirm_assistant_action(
    payload: AssistantConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm or cancel a pending AI action preview."""
    try:
        result = execute_confirmed_action(db, current_user.id, payload.audit_id, payload.confirm)
        return AssistantConfirmResponse(
            message=result["message"],
            audit_id=payload.audit_id,
            status=result["status"],
            result=result.get("result"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assistant action failed.") from exc


@router.get("/history", response_model=list[AssistantHistoryResponse])
def get_assistant_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return recent assistant chat history for the current user."""
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == current_user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(50)
        .all()
    )
