from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import AdvisorChat, AdvisorMessage, AdvisorRecommendation, User
from app.schemas.schemas import (
    AdvisorAskRequest,
    AdvisorAskResponse,
    AdvisorActionRequest,
    AdvisorActionResponse,
    AdvisorChatCreate,
    AdvisorChatDetailResponse,
    AdvisorChatResponse,
    AdvisorMessageResponse,
    AdvisorRecommendationResponse,
    AdvisorRecommendationStatusUpdate,
)
from app.services.advisor_actions_service import run_advisor_action
from app.services.advisor_service import ask_financial_advisor

router = APIRouter(prefix="/advisor", tags=["ai advisor"])


@router.post("/ask", response_model=AdvisorAskResponse)
def ask_advisor(
    payload: AdvisorAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ask_financial_advisor(
        db,
        current_user.id,
        payload.question,
        chat_id=payload.chat_id,
        month=payload.month,
        year=payload.year,
    )


@router.post("/actions", response_model=AdvisorActionResponse)
def run_advisor_action_endpoint(
    payload: AdvisorActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return run_advisor_action(db, current_user.id, payload.message)


@router.post("/chats", response_model=AdvisorChatResponse, status_code=status.HTTP_201_CREATED)
def create_advisor_chat(
    payload: AdvisorChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = AdvisorChat(user_id=current_user.id, title=payload.title or "New advisor chat")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/chats", response_model=list[AdvisorChatResponse])
def get_advisor_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(AdvisorChat)
        .filter(AdvisorChat.user_id == current_user.id)
        .order_by(AdvisorChat.updated_at.desc(), AdvisorChat.created_at.desc())
        .all()
    )


@router.get("/chats/{chat_id}", response_model=AdvisorChatDetailResponse)
def get_advisor_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = db.query(AdvisorChat).filter(AdvisorChat.id == chat_id, AdvisorChat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advisor chat not found")

    messages = (
        db.query(AdvisorMessage)
        .filter(AdvisorMessage.chat_id == chat.id)
        .order_by(AdvisorMessage.created_at.asc(), AdvisorMessage.id.asc())
        .all()
    )
    return AdvisorChatDetailResponse(
        id=chat.id,
        user_id=chat.user_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[
            AdvisorMessageResponse(
                id=message.id,
                chat_id=message.chat_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.get("/recommendations", response_model=list[AdvisorRecommendationResponse])
def get_advisor_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(AdvisorRecommendation)
        .filter(AdvisorRecommendation.user_id == current_user.id)
        .order_by(AdvisorRecommendation.created_at.desc())
        .all()
    )


@router.patch("/recommendations/{recommendation_id}", response_model=AdvisorRecommendationResponse)
def update_advisor_recommendation(
    recommendation_id: int,
    payload: AdvisorRecommendationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recommendation = (
        db.query(AdvisorRecommendation)
        .filter(
            AdvisorRecommendation.id == recommendation_id,
            AdvisorRecommendation.user_id == current_user.id,
        )
        .first()
    )
    if not recommendation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    recommendation.status = payload.status
    db.commit()
    db.refresh(recommendation)
    return recommendation
