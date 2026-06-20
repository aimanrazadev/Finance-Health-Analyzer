from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Friend, User
from app.schemas.schemas import (
    FriendCreate,
    FriendCreateResponse,
    FriendDashboardResponse,
    FriendDetailResponse,
    FriendResponse,
    FriendUpdate,
)
from app.services.friend_service import (
    create_or_update_friend_from_name,
    get_friend_dashboard,
    get_friend_detail,
    hide_friend,
    link_matching_transactions,
    refresh_friend_stats,
)
from app.services.friend_detection_service import display_friend_name, normalize_friend_key

router = APIRouter(prefix="/friends", tags=["friends"])


@router.post("", response_model=FriendCreateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FriendCreateResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def add_friend(
    payload: FriendCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create/update a friend and link all historical matching transactions."""
    try:
        friend, linked_count = create_or_update_friend_from_name(db, current_user.id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    db.refresh(friend)
    return FriendCreateResponse(
        friend=friend,
        linked_transactions=linked_count,
        message=f"{friend.name} is ready with {friend.transaction_count} linked transaction(s).",
    )


@router.get("", response_model=List[FriendResponse])
@router.get("/", response_model=List[FriendResponse], include_in_schema=False)
def list_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return visible friends with refreshed transaction totals."""
    friends = (
        db.query(Friend)
        .filter(Friend.user_id == current_user.id, Friend.is_hidden == False)  # noqa: E712
        .order_by(Friend.name.asc())
        .all()
    )
    for friend in friends:
        refresh_friend_stats(db, friend)
    db.commit()
    return friends


@router.get("/dashboard", response_model=FriendDashboardResponse)
def friends_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Friend module summary plus friend cards."""
    dashboard = get_friend_dashboard(db, current_user.id)
    db.commit()
    return dashboard


@router.get("/{friend_id}", response_model=FriendDetailResponse)
def friend_details(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Show one friend with only transactions linked to that friend."""
    friend, transactions = get_friend_detail(db, current_user.id, friend_id)
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")
    db.commit()
    return FriendDetailResponse(friend=friend, transactions=transactions)


@router.put("/{friend_id}", response_model=FriendCreateResponse)
def update_friend(
    friend_id: int,
    payload: FriendUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a friend, refresh learning, and re-link matching transactions."""
    friend = (
        db.query(Friend)
        .filter(Friend.id == friend_id, Friend.user_id == current_user.id)
        .first()
    )
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")

    normalized = normalize_friend_key(payload.name)
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Friend name is required")

    friend.name = display_friend_name(payload.name)
    friend.normalized_name = normalized
    friend.is_hidden = False
    linked_count = link_matching_transactions(db, current_user.id, friend)
    db.commit()
    db.refresh(friend)
    return FriendCreateResponse(
        friend=friend,
        linked_transactions=linked_count,
        message=f"{friend.name} updated.",
    )


@router.delete("/{friend_id}", response_model=FriendResponse)
def delete_or_hide_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hide a friend while keeping linked transaction history safe."""
    friend = hide_friend(db, current_user.id, friend_id)
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")
    db.commit()
    db.refresh(friend)
    return friend
