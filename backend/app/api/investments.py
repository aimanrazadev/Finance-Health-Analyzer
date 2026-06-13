import json
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import AccountBalance, Category, InvestmentHolding, SavingsGoal, Transaction, User
from app.schemas.schemas import (
    AccountBalanceCreate,
    AccountBalanceResponse,
    InvestmentHoldingCreate,
    InvestmentHoldingResponse,
    InvestmentHoldingUpdate,
    InvestmentInsightResponse,
    InvestmentSummaryResponse,
)

router = APIRouter(prefix="/investments", tags=["investments"])


def normalize_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Normalize Indian stock symbols for public market quote lookups."""
    cleaned = symbol.strip().upper()
    if "." in cleaned:
        return cleaned
    if exchange.strip().upper() == "BSE":
        return f"{cleaned}.BO"
    return f"{cleaned}.NS"


def fetch_public_market_price(symbol: str, exchange: str = "NSE") -> float | None:
    """Fetch a best-effort public quote without storing brokerage credentials."""
    yahoo_symbol = normalize_symbol(symbol, exchange)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1d&range=1d"
    request = Request(url, headers={"User-Agent": "FinSightAI/1.0"})
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None

    result = payload.get("chart", {}).get("result") or []
    if not result:
        return None
    meta = result[0].get("meta", {})
    price = meta.get("regularMarketPrice") or meta.get("previousClose")
    return float(price) if price else None


def recalculate_holding(holding: InvestmentHolding, current_price: float | None = None) -> InvestmentHolding:
    """Recalculate invested amount, current value, and profit/loss for one holding."""
    holding.invested_amount = round(float(holding.quantity) * float(holding.average_buy_price), 2)
    if current_price is not None:
        holding.current_price = float(current_price)
        holding.last_price_at = datetime.utcnow()

    price = holding.current_price or holding.average_buy_price
    holding.current_value = round(float(holding.quantity) * float(price), 2)
    holding.pnl_amount = round(holding.current_value - holding.invested_amount, 2)
    holding.pnl_percent = round((holding.pnl_amount / holding.invested_amount * 100), 2) if holding.invested_amount else 0
    return holding


def get_holding_or_404(db: Session, user_id: int, holding_id: int) -> InvestmentHolding:
    """Fetch a user-owned holding or raise 404."""
    holding = db.query(InvestmentHolding).filter(InvestmentHolding.id == holding_id, InvestmentHolding.user_id == user_id).first()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investment holding not found")
    return holding


def get_investment_category_id(db: Session) -> int | None:
    """Find the Investments category used by upload categorization."""
    category = db.query(Category).filter(func.lower(Category.name) == "investments").first()
    return category.id if category else None


def get_auto_detected_investment_amount(db: Session, user_id: int) -> float:
    """Sum uploaded/manual transactions categorized as Investments."""
    investment_category_id = get_investment_category_id(db)
    filters = [
        Transaction.user_id == user_id,
        Transaction.transaction_type == "expense",
    ]
    if investment_category_id:
        filters.append(Transaction.category_id == investment_category_id)
    else:
        filters.append(Transaction.description.ilike("%investment%"))
    return float(db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(*filters).scalar() or 0)


def build_investment_insights(
    account_balance: AccountBalance | None,
    manual_invested: float,
    auto_detected: float,
    current_value: float,
    pnl_amount: float,
) -> list[InvestmentInsightResponse]:
    """Create simple explainable portfolio insights from current values."""
    insights: list[InvestmentInsightResponse] = []
    if current_value > 0:
        severity = "positive" if pnl_amount >= 0 else "warning"
        direction = "profit" if pnl_amount >= 0 else "loss"
        insights.append(InvestmentInsightResponse(
            title="Portfolio P/L",
            message=f"Your manually tracked portfolio is currently in {direction} by INR {abs(pnl_amount):,.0f}.",
            severity=severity,
        ))

    if auto_detected > manual_invested * 0.10 and auto_detected > 0:
        insights.append(InvestmentInsightResponse(
            title="PDF investment flow detected",
            message=f"Uploaded transactions show INR {auto_detected:,.0f} categorized as Investments. Match this against your holdings to keep portfolio tracking accurate.",
            severity="info",
        ))

    if account_balance and account_balance.balance_amount < max(5000, current_value * 0.03):
        insights.append(InvestmentInsightResponse(
            title="Cash balance looks tight",
            message="Your entered current balance is low compared with your tracked portfolio. Review spending before adding more investments.",
            severity="warning",
        ))

    if not insights:
        insights.append(InvestmentInsightResponse(
            title="Start tracking safely",
            message="Add your current balance and at least one holding to see portfolio value, profit/loss, and dashboard analysis.",
            severity="info",
        ))
    return insights


@router.get("/summary", response_model=InvestmentSummaryResponse)
def get_investment_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return manual balance, holdings, public quote valuation, and portfolio insights."""
    savings_totals = (
        db.query(
            func.coalesce(func.sum(SavingsGoal.target_amount), 0),
            func.coalesce(func.sum(SavingsGoal.current_amount), 0),
        )
        .filter(SavingsGoal.user_id == current_user.id)
        .first()
    )
    account_balance = (
        db.query(AccountBalance)
        .filter(AccountBalance.user_id == current_user.id)
        .order_by(AccountBalance.updated_at.desc(), AccountBalance.recorded_at.desc())
        .first()
    )
    holdings = (
        db.query(InvestmentHolding)
        .filter(InvestmentHolding.user_id == current_user.id)
        .order_by(InvestmentHolding.updated_at.desc())
        .all()
    )
    manual_invested = round(sum(float(holding.invested_amount or 0) for holding in holdings), 2)
    current_value = round(sum(float(holding.current_value or 0) for holding in holdings), 2)
    pnl_amount = round(current_value - manual_invested, 2)
    pnl_percent = round((pnl_amount / manual_invested * 100), 2) if manual_invested else 0
    auto_detected = get_auto_detected_investment_amount(db, current_user.id)
    net_worth = round((account_balance.balance_amount if account_balance else 0) + current_value, 2)

    return InvestmentSummaryResponse(
        savings_goal_total=float(savings_totals[0] or 0),
        savings_current_total=float(savings_totals[1] or 0),
        account_balance=account_balance,
        manual_invested_amount=manual_invested,
        auto_detected_invested_amount=round(auto_detected, 2),
        total_invested_amount=round(manual_invested + auto_detected, 2),
        current_portfolio_value=current_value,
        total_pnl_amount=pnl_amount,
        total_pnl_percent=pnl_percent,
        net_worth=net_worth,
        holdings=holdings,
        insights=build_investment_insights(account_balance, manual_invested, auto_detected, current_value, pnl_amount),
    )


@router.post("/balance", response_model=AccountBalanceResponse)
def upsert_account_balance(
    payload: AccountBalanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save the user's manually entered current bank/cash balance."""
    balance = db.query(AccountBalance).filter(AccountBalance.user_id == current_user.id).first()
    if not balance:
        balance = AccountBalance(user_id=current_user.id, currency="INR")
        db.add(balance)
    balance.account_name = payload.account_name.strip()
    balance.balance_amount = payload.balance_amount
    db.commit()
    db.refresh(balance)
    return balance


@router.post("/holdings", response_model=InvestmentHoldingResponse, status_code=status.HTTP_201_CREATED)
def create_holding(
    payload: InvestmentHoldingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a manually entered investment holding."""
    public_price = fetch_public_market_price(payload.symbol, payload.exchange)
    holding = InvestmentHolding(
        user_id=current_user.id,
        asset_name=payload.asset_name.strip(),
        symbol=payload.symbol.strip().upper(),
        exchange=payload.exchange.strip().upper(),
        quantity=payload.quantity,
        average_buy_price=payload.average_buy_price,
        current_price=payload.current_price or public_price,
        source="manual",
    )
    recalculate_holding(holding)
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.put("/holdings/{holding_id}", response_model=InvestmentHoldingResponse)
def update_holding(
    holding_id: int,
    payload: InvestmentHoldingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a user-owned investment holding."""
    holding = get_holding_or_404(db, current_user.id, holding_id)
    holding.asset_name = payload.asset_name.strip()
    holding.symbol = payload.symbol.strip().upper()
    holding.exchange = payload.exchange.strip().upper()
    holding.quantity = payload.quantity
    holding.average_buy_price = payload.average_buy_price
    recalculate_holding(holding, payload.current_price)
    db.commit()
    db.refresh(holding)
    return holding


@router.post("/holdings/{holding_id}/refresh-price", response_model=InvestmentHoldingResponse)
def refresh_holding_price(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Refresh one holding with a public market quote if available."""
    holding = get_holding_or_404(db, current_user.id, holding_id)
    public_price = fetch_public_market_price(holding.symbol, holding.exchange)
    if public_price is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Public quote is currently unavailable")
    recalculate_holding(holding, public_price)
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a user-owned manual investment holding."""
    holding = get_holding_or_404(db, current_user.id, holding_id)
    db.delete(holding)
    db.commit()
    return None
