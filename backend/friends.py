from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Debt, Friend, Transaction, User
from schemas import (
    DebtCreate,
    DebtResponse,
    DebtUpdate,
    FriendCreate,
    FriendDashboardSummary,
    FriendDetailResponse,
    FriendPaymentRequest,
    FriendSuggestionResponse,
    FriendSummary,
    FriendUpdate,
    LinkFriendRequest,
    SplitExpenseRequest,
)
from services.debt_service import create_debt, link_transaction_to_friend, unlink_transaction_from_friend
from services.friend_detection_service import detect_friend_for_transaction
from services.friend_service import auto_attach_matching_transactions, get_friend_dashboard, normalize_friend_name, summarize_friend
from services.settlement_service import settle_friend_balance
from services.split_expense_service import create_split_expense

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
    debts = db.query(Debt).filter(Debt.user_id == current_user.id, Debt.friend_id == friend.id).order_by(Debt.created_at.desc()).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.friend_id == friend.id).order_by(Transaction.date.desc()).all()
    return {"friend": summarize_friend(db, friend), "debts": debts, "transactions": transactions}


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


@router.post("/friends/{friend_id}/debts", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
def add_friend_debt(friend_id: int, payload: DebtCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_friend_or_404(db, current_user.id, friend_id)
    debt = create_debt(db, current_user.id, friend_id, payload.amount, payload.debt_type, payload.direction, payload.transaction_id, payload.note)
    db.commit()
    db.refresh(debt)
    return debt


@router.get("/friends/{friend_id}/debts", response_model=list[DebtResponse])
def list_friend_debts(friend_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_friend_or_404(db, current_user.id, friend_id)
    return db.query(Debt).filter(Debt.user_id == current_user.id, Debt.friend_id == friend_id).order_by(Debt.created_at.desc()).all()


@router.patch("/debts/{debt_id}", response_model=DebtResponse)
def update_debt(debt_id: int, payload: DebtUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    debt = db.query(Debt).filter(Debt.id == debt_id, Debt.user_id == current_user.id).first()
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(debt, field, value)
    db.commit()
    db.refresh(debt)
    return debt


@router.delete("/debts/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debt(debt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    debt = db.query(Debt).filter(Debt.id == debt_id, Debt.user_id == current_user.id).first()
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    db.delete(debt)
    db.commit()


@router.post("/transactions/{transaction_id}/link-friend", response_model=DebtResponse)
def link_friend(transaction_id: int, payload: LinkFriendRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_friend_or_404(db, current_user.id, payload.friend_id)
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    try:
        debt = link_transaction_to_friend(db, current_user.id, transaction, payload.friend_id, payload.debt_type, payload.debt_direction, payload.amount, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(debt)
    return debt


@router.post("/transactions/{transaction_id}/unlink-friend")
def unlink_friend(transaction_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    unlink_transaction_from_friend(db, current_user.id, transaction)
    db.commit()
    return {"message": "Friend link removed and balance recalculated."}


@router.get("/transactions/friend-suggestions", response_model=list[FriendSuggestionResponse])
def get_friend_suggestions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.is_friend_transaction == False).all()  # noqa: E712
    suggestions = [detect_friend_for_transaction(db, current_user.id, transaction) for transaction in transactions]
    return [item for item in suggestions if item]


@router.post("/friends/{friend_id}/settle")
def settle_friend(friend_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend = get_friend_or_404(db, current_user.id, friend_id)
    settlement = settle_friend_balance(db, current_user.id, friend)
    db.commit()
    return {"message": "Friend balance settled.", "settlement_id": settlement.id}


@router.post("/friends/{friend_id}/payment", response_model=DebtResponse)
def add_friend_payment(friend_id: int, payload: FriendPaymentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_friend_or_404(db, current_user.id, friend_id)
    debt = create_debt(db, current_user.id, friend_id, payload.amount, payload.debt_type, payload.direction, note=payload.note)
    db.commit()
    db.refresh(debt)
    return debt


@router.post("/friends/split-expense", response_model=list[DebtResponse])
def split_expense(payload: SplitExpenseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transaction = None
    if payload.transaction_id:
        transaction = db.query(Transaction).filter(Transaction.id == payload.transaction_id, Transaction.user_id == current_user.id).first()
        if not transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    for share in payload.shares:
        get_friend_or_404(db, current_user.id, share.friend_id)
    debts = create_split_expense(db, current_user.id, payload.total_amount, payload.shares, transaction, payload.description)
    db.commit()
    return debts
