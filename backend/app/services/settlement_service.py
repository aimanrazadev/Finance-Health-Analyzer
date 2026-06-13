from sqlalchemy.orm import Session

from app.models.models import Debt, Friend, FriendSettlement
from app.services.debt_service import create_debt
from app.services.friend_service import summarize_friend


def settle_friend_balance(db: Session, user_id: int, friend: Friend, note: str | None = None) -> FriendSettlement:
    """Create an audit settlement that brings a friend's net balance to zero."""
    summary = summarize_friend(db, friend)
    net_balance = summary["net_balance"]
    if net_balance == 0:
        amount = 0
        settlement_type = "already_settled"
    elif net_balance > 0:
        amount = net_balance
        settlement_type = "friend_paid_back"
        create_debt(db, user_id, friend.id, amount, "friend_repayment", "reduces_friend_debt", note=note or "Manually settled")
    else:
        amount = abs(net_balance)
        settlement_type = "my_repayment"
        create_debt(db, user_id, friend.id, amount, "my_repayment", "reduces_my_debt", note=note or "Manually settled")

    db.query(Debt).filter(Debt.user_id == user_id, Debt.friend_id == friend.id).update({"status": "paid"})
    settlement = FriendSettlement(
        user_id=user_id,
        friend_id=friend.id,
        amount=amount,
        settlement_type=settlement_type,
        note=note or "Manually settled",
    )
    db.add(settlement)
    return settlement
