from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Friend, Transaction, User
from app.schemas.schemas import (
    FriendCreate,
    FriendDashboardResponse,
    FriendDetailResponse,
    FriendResponse,
    FriendUpdate,
)
from app.services.friend_service import (
    auto_attach_matching_transactions,
    create_friend,
    friend_summary,
    get_friend_dashboard,
    merge_duplicate_friends,
    normalize_friend_name,
    normalize_existing_friends,
)
from app.services.friend_detection_service import canonical_friend_display_name

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("/dashboard", response_model=FriendDashboardResponse)
def get_friends_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_friend_dashboard(db, current_user.id)


@router.get("", response_model=list[FriendResponse])
@router.get("/", response_model=list[FriendResponse], include_in_schema=False)
def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_hidden: bool = False,
):
    normalize_existing_friends(db, current_user.id)
    db.commit()
    query = db.query(Friend).filter(Friend.user_id == current_user.id)
    if not include_hidden:
        query = query.filter(or_(Friend.is_active == True, Friend.is_active.is_(None)))  # noqa: E712
    return query.order_by(Friend.name.asc()).all()


@router.post("", response_model=FriendResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FriendResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def add_friend(
    payload: FriendCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        friend = create_friend(
            db,
            current_user.id,
            payload.name,
            email=payload.email,
            phone=payload.phone,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    db.refresh(friend)
    return friend


@router.get("/{friend_id}", response_model=FriendDetailResponse)
def get_friend_detail(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalize_existing_friends(db, current_user.id)
    db.commit()
    friend = db.query(Friend).filter(Friend.id == friend_id, Friend.user_id == current_user.id).first()
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")
    if friend.is_active is False and "__merged_" in (friend.normalized_name or ""):
        canonical_key = normalize_friend_name(canonical_friend_display_name(friend.name) or friend.name)
        primary_friend = (
            db.query(Friend)
            .filter(
                Friend.user_id == current_user.id,
                Friend.normalized_name == canonical_key,
                or_(Friend.is_active == True, Friend.is_active.is_(None)),  # noqa: E712
            )
            .order_by(Friend.id.asc())
            .first()
        )
        if primary_friend:
            friend = primary_friend

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.friend_id == friend.id,
            Transaction.is_friend_transaction == True,  # noqa: E712
        )
        .order_by(Transaction.date.desc())
        .all()
    )
    return FriendDetailResponse(
        id=friend.id,
        user_id=friend.user_id,
        name=friend.name,
        normalized_name=friend.normalized_name,
        email=friend.email,
        phone=friend.phone,
        notes=friend.notes,
        is_active=friend.is_active,
        created_at=friend.created_at,
        summary=friend_summary(db, current_user.id, friend.id),
        transactions=transactions,
    )


@router.put("/{friend_id}", response_model=FriendResponse)
def update_friend(
    friend_id: int,
    payload: FriendUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend = db.query(Friend).filter(Friend.id == friend_id, Friend.user_id == current_user.id).first()
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")

    if payload.name is not None:
        display_name = canonical_friend_display_name(payload.name) or payload.name.strip()
        friend.name = display_name
        friend.normalized_name = normalize_friend_name(display_name)
    if payload.email is not None:
        friend.email = payload.email
    if payload.phone is not None:
        friend.phone = payload.phone
    if payload.notes is not None:
        friend.notes = payload.notes
    if payload.is_active is not None:
        friend.is_active = payload.is_active

    if friend.is_active:
        friend = merge_duplicate_friends(db, current_user.id, friend.normalized_name) or friend
        auto_attach_matching_transactions(db, current_user.id, friend)

    db.commit()
    db.refresh(friend)
    return friend


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def hide_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend = db.query(Friend).filter(Friend.id == friend_id, Friend.user_id == current_user.id).first()
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")

    # Soft-hide only. Existing transaction links remain for history safety.
    friend.is_active = False
    db.commit()
