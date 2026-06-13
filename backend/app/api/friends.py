from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Category, Friend, FriendTransactionLink, Transaction, User
from app.schemas.schemas import (
    FriendCreate,
    FriendDashboardSummary,
    FriendDetailResponse,
    FriendSuggestionResponse,
    FriendSummary,
    FriendUpdate,
    LinkFriendRequest,
)
from app.services.friend_detection_service import detect_friend_for_transaction
from app.services.friend_service import auto_attach_matching_transactions, get_friend_dashboard, normalize_friend_name, summarize_friend

router = APIRouter(tags=["friends"])


def get_friend_or_404(db: Session, user_id: int, friend_id: int) -> Friend:
    friend = db.query(Friend).filter(Friend.id == friend_id, Friend.user_id == user_id).first()
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")
    return friend


@router.post("/friends", response_model=FriendSummary, status_code=status.HTTP_201_CREATED)
def create_friend(payload: FriendCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized_name = normalize_friend_name(payload.name)
    if not normalized_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Friend name cannot be empty")
    friend = Friend(user_id=current_user.id, name=payload.name.strip(), normalized_name=normalized_name, phone=payload.phone, note=payload.note)
    db.add(friend)
    db.flush()
    auto_attach_matching_transactions(db, current_user.id, friend)
    db.commit()
    db.refresh(friend)
    return summarize_friend(db, friend)


@router.get("/friends", response_model=FriendDashboardSummary)
def list_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: str | None = None,
    include_archived: bool = False,
):
    return get_friend_dashboard(db, current_user.id, include_archived, search)


@router.get("/friends/{friend_id}", response_model=FriendDetailResponse)
def get_friend_detail(friend_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend = get_friend_or_404(db, current_user.id, friend_id)
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.friend_id == friend.id).order_by(Transaction.date.desc()).all()
    return {"friend": summarize_friend(db, friend), "transactions": transactions}


@router.patch("/friends/{friend_id}", response_model=FriendSummary)
def update_friend(friend_id: int, payload: FriendUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend = get_friend_or_404(db, current_user.id, friend_id)
    if payload.name is not None:
        friend.name = payload.name.strip()
        friend.normalized_name = normalize_friend_name(payload.name)
    if payload.phone is not None:
        friend.phone = payload.phone
    if payload.note is not None:
        friend.note = payload.note
    if payload.is_archived is not None:
        friend.is_archived = payload.is_archived
    auto_attach_matching_transactions(db, current_user.id, friend)
    db.commit()
    db.refresh(friend)
    return summarize_friend(db, friend)


@router.delete("/friends/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_friend(friend_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend = get_friend_or_404(db, current_user.id, friend_id)
    friend.is_archived = True
    db.commit()


def get_friends_category_id(db: Session) -> int:
    category = db.query(Category).filter(Category.name == "Friends").first()
    if category:
        return category.id
    category = Category(name="Friends", description="Friend-linked transactions")
    db.add(category)
    db.flush()
    return category.id


@router.post("/transactions/{transaction_id}/link-friend")
def link_friend(transaction_id: int, payload: LinkFriendRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend = get_friend_or_404(db, current_user.id, payload.friend_id)
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    transaction.original_category_id = transaction.original_category_id or transaction.category_id
    transaction.category_id = get_friends_category_id(db)
    transaction.friend_id = friend.id
    transaction.debt_type = None
    transaction.debt_direction = None
    transaction.is_friend_transaction = True
    transaction.is_needs_review = False
    transaction.review_status = "approved"
    transaction.review_reason = None
    transaction.categorization_method = "friend_match"
    transaction.category_confidence = 0.95
    existing_link = (
        db.query(FriendTransactionLink)
        .filter(
            FriendTransactionLink.user_id == current_user.id,
            FriendTransactionLink.friend_id == friend.id,
            FriendTransactionLink.transaction_id == transaction.id,
        )
        .first()
    )
    if not existing_link:
        db.add(FriendTransactionLink(user_id=current_user.id, friend_id=friend.id, transaction_id=transaction.id))
    db.commit()
    db.refresh(transaction)
    return {"message": f"Transaction linked to {friend.name}.", "transaction": transaction}


@router.post("/transactions/{transaction_id}/unlink-friend")
def unlink_friend(transaction_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    db.query(FriendTransactionLink).filter(FriendTransactionLink.user_id == current_user.id, FriendTransactionLink.transaction_id == transaction.id).delete(synchronize_session=False)
    transaction.friend_id = None
    transaction.debt_type = None
    transaction.debt_direction = None
    transaction.is_friend_transaction = False
    db.commit()
    return {"message": "Friend link removed."}


@router.get("/transactions/friend-suggestions", response_model=list[FriendSuggestionResponse])
def get_friend_suggestions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.is_friend_transaction == False).all()  # noqa: E712
    suggestions = [detect_friend_for_transaction(db, current_user.id, transaction) for transaction in transactions]
    return [item for item in suggestions if item]
