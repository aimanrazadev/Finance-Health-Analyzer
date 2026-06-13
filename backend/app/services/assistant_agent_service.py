import json
import re
from calendar import monthrange
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.models import AiActionAudit, Budget, Category, Friend, SavingsGoal, Transaction
from app.services.friend_service import normalize_friend_name
from app.services.subscription_service import list_active_subscriptions


WRITE_INTENTS = {
    "update_transaction_category",
    "bulk_update_transaction_category",
    "mark_transaction_reviewed",
    "link_transaction_to_friend",
    "unlink_transaction_from_friend",
    "rename_transaction_merchant",
    "create_budget",
    "update_budget",
    "create_savings_goal",
    "update_savings_goal",
}


def _current_month_bounds() -> tuple[datetime, datetime, int, int]:
    today = datetime.now()
    start = datetime(today.year, today.month, 1)
    end = datetime(today.year, today.month, monthrange(today.year, today.month)[1], 23, 59, 59)
    return start, end, today.month, today.year


def _extract_transaction_id(message: str) -> int | None:
    match = re.search(r"\b(?:transaction|txn|id)\s*#?\s*(\d+)\b", message, flags=re.I)
    return int(match.group(1)) if match else None


def _extract_category(db: Session, message: str) -> Category | None:
    categories = db.query(Category).all()
    text = message.lower()
    return next((category for category in categories if category.name.lower() in text), None)


def _extract_keyword(message: str) -> str | None:
    patterns = [
        r"\bfor\s+(.+)$",
        r"\bwith\s+(.+)$",
        r"\bto\s+(.+)$",
        r"\bsearch\s+transactions\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.I)
        if match:
            value = re.sub(r"\b(this|month|category|friend|reviewed|review)\b", "", match.group(1), flags=re.I)
            value = value.strip(" .")
            if value:
                return value
    return None


def _serialize_transaction(row: Transaction) -> dict[str, Any]:
    return {
        "id": row.id,
        "description": row.description,
        "merchant": row.merchant,
        "amount": row.amount,
        "transaction_type": row.transaction_type,
        "date": row.date.isoformat() if row.date else None,
        "category_id": row.category_id,
        "friend_id": row.friend_id,
    }


def detect_intent(message: str) -> str:
    text = message.lower()
    if any(term in text for term in ["sql", "drop table", "delete database", "truncate"]):
        return "unsafe_sql_blocked"
    if ("change" in text or "update" in text or "move" in text) and "category" in text:
        return "bulk_update_transaction_category" if "all" in text else "update_transaction_category"
    if "mark" in text and "review" in text:
        return "mark_transaction_reviewed"
    if "unlink" in text and "friend" in text:
        return "unlink_transaction_from_friend"
    if "link" in text and "friend" in text:
        return "link_transaction_to_friend"
    if "create" in text and "budget" in text:
        return "create_budget"
    if "update" in text and "budget" in text:
        return "update_budget"
    if ("create" in text or "add" in text) and ("goal" in text or "savings" in text):
        return "create_savings_goal"
    if "update" in text and ("goal" in text or "savings" in text):
        return "update_savings_goal"
    if "merchant" in text and ("rename" in text or "change" in text):
        return "rename_transaction_merchant"
    if "budget" in text:
        return "get_budget_status"
    if "subscription" in text or "recurring" in text:
        return "get_subscriptions"
    if "goal" in text or "savings goal" in text:
        return "get_savings_goals"
    if "merchant" in text or "top" in text:
        return "get_top_merchants"
    if "category" in text or "spending" in text:
        return "get_spending_by_category"
    if "friend" in text or "sent" in text or "received" in text:
        if "sent" in text:
            return "get_friend_sent_amount"
        if "received" in text:
            return "get_friend_received_amount"
        return "get_friend_transactions"
    if "search" in text or "transaction" in text:
        return "search_transactions"
    if "unusual" in text or "anomaly" in text:
        return "detect_unusual_spending"
    if "last month" in text or "compare" in text:
        return "compare_months"
    return "get_monthly_summary"


def _audit_preview(db: Session, user_id: int, action_type: str, request_text: str, preview: dict) -> AiActionAudit:
    audit = AiActionAudit(
        user_id=user_id,
        action_type=action_type,
        status="previewed",
        request_text=request_text,
        preview_payload=json.dumps(preview, default=str),
        requires_confirmation=True,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def _transactions_by_keyword(db: Session, user_id: int, keyword: str, current_month_only: bool = False, limit: int = 100) -> list[Transaction]:
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if current_month_only:
        start, end, _month, _year = _current_month_bounds()
        query = query.filter(Transaction.date >= start, Transaction.date <= end)
    term = f"%{keyword}%"
    return (
        query.filter(or_(Transaction.description.ilike(term), Transaction.merchant.ilike(term)))
        .order_by(Transaction.date.desc())
        .limit(limit)
        .all()
    )


def get_monthly_summary(db: Session, user_id: int) -> dict:
    start, end, month, year = _current_month_bounds()
    income = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.user_id == user_id, Transaction.transaction_type == "income", Transaction.date >= start, Transaction.date <= end).scalar()
    expenses = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense", Transaction.date >= start, Transaction.date <= end).scalar()
    count = db.query(func.count(Transaction.id)).filter(Transaction.user_id == user_id, Transaction.date >= start, Transaction.date <= end).scalar()
    return {"month": month, "year": year, "income": float(income or 0), "expenses": float(expenses or 0), "savings": float(income or 0) - float(expenses or 0), "transaction_count": int(count or 0)}


def get_spending_by_category(db: Session, user_id: int) -> dict:
    start, end, _month, _year = _current_month_bounds()
    rows = (
        db.query(Category.name, func.coalesce(func.sum(Transaction.amount), 0))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense", Transaction.date >= start, Transaction.date <= end)
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    return {"categories": [{"category": name or "Uncategorized", "amount": float(total or 0)} for name, total in rows]}


def get_top_merchants(db: Session, user_id: int) -> dict:
    start, end, _month, _year = _current_month_bounds()
    rows = (
        db.query(Transaction.merchant, func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense", Transaction.date >= start, Transaction.date <= end, Transaction.merchant.isnot(None))
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
        .all()
    )
    return {"merchants": [{"merchant": merchant or "Unknown", "amount": float(total or 0)} for merchant, total in rows]}


def search_transactions(db: Session, user_id: int, message: str) -> dict:
    keyword = _extract_keyword(message) or message
    rows = _transactions_by_keyword(db, user_id, keyword, limit=20)
    return {"keyword": keyword, "transactions": [_serialize_transaction(row) for row in rows]}


def get_budget_status(db: Session, user_id: int) -> dict:
    budgets = db.query(Budget).filter(Budget.user_id == user_id, Budget.is_active == True).all()  # noqa: E712
    return {"budgets": [{"id": row.id, "category_id": row.category_id, "amount": row.amount, "period": row.period} for row in budgets]}


def get_savings_goals(db: Session, user_id: int) -> dict:
    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).order_by(SavingsGoal.created_at.desc()).all()
    return {"goals": [{"id": goal.id, "name": goal.name, "target_amount": goal.target_amount, "current_amount": goal.current_amount, "status": goal.status} for goal in goals]}


def get_subscriptions(db: Session, user_id: int) -> dict:
    return list_active_subscriptions(db, user_id)


def get_friend_transactions(db: Session, user_id: int, message: str) -> dict:
    keyword = _extract_keyword(message)
    if not keyword:
        return {"friend": None, "transactions": []}
    normalized = normalize_friend_name(keyword)
    friend = db.query(Friend).filter(Friend.user_id == user_id, Friend.normalized_name.ilike(f"%{normalized}%"), Friend.is_archived == False).first()  # noqa: E712
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if friend:
        query = query.filter(Transaction.friend_id == friend.id)
    else:
        query = query.filter(or_(Transaction.description.ilike(f"%{keyword}%"), Transaction.merchant.ilike(f"%{keyword}%")))
    rows = query.order_by(Transaction.date.desc()).limit(20).all()
    return {"friend": friend.name if friend else keyword, "transactions": [_serialize_transaction(row) for row in rows]}


def get_friend_amount(db: Session, user_id: int, message: str, transaction_type: str) -> dict:
    data = get_friend_transactions(db, user_id, message)
    rows = [row for row in data["transactions"] if row["transaction_type"] == transaction_type]
    return {"friend": data["friend"], "transaction_type": transaction_type, "total": round(sum(row["amount"] for row in rows), 2), "transactions": rows}


def detect_unusual_spending(db: Session, user_id: int) -> dict:
    rows = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense").order_by(Transaction.amount.desc()).limit(5).all()
    return {"transactions": [_serialize_transaction(row) for row in rows]}


def compare_months(db: Session, user_id: int) -> dict:
    current = get_monthly_summary(db, user_id)
    now = datetime.now()
    previous_month = 12 if now.month == 1 else now.month - 1
    previous_year = now.year - 1 if now.month == 1 else now.year
    start = datetime(previous_year, previous_month, 1)
    end = datetime(previous_year, previous_month, monthrange(previous_year, previous_month)[1], 23, 59, 59)
    previous_expenses = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense", Transaction.date >= start, Transaction.date <= end).scalar()
    return {"current_expenses": current["expenses"], "previous_expenses": float(previous_expenses or 0), "difference": current["expenses"] - float(previous_expenses or 0)}


def _preview_update_category(db: Session, user_id: int, message: str, bulk: bool) -> tuple[str, AiActionAudit | None, dict]:
    category = _extract_category(db, message)
    keyword = _extract_keyword(message)
    if not category or not keyword:
        return "Tell me which transactions and category, for example: Change all Zomato transactions to Food.", None, {}
    rows = _transactions_by_keyword(db, user_id, keyword, current_month_only="this month" in message.lower(), limit=100 if bulk else 1)
    preview = {"category_id": category.id, "category_name": category.name, "transaction_ids": [row.id for row in rows], "matched_count": len(rows), "sample": [_serialize_transaction(row) for row in rows[:10]]}
    audit = _audit_preview(db, user_id, "bulk_update_transaction_category" if bulk else "update_transaction_category", message, preview)
    return f"Preview ready: update {len(rows)} transaction(s) to {category.name}.", audit, preview


def _preview_mark_reviewed(db: Session, user_id: int, message: str) -> tuple[str, AiActionAudit | None, dict]:
    transaction_id = _extract_transaction_id(message)
    if not transaction_id:
        return "Tell me the transaction id to mark as reviewed.", None, {}
    row = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.id == transaction_id).first()
    if not row:
        return "I could not find that transaction.", None, {}
    preview = {"transaction_ids": [row.id], "sample": [_serialize_transaction(row)]}
    audit = _audit_preview(db, user_id, "mark_transaction_reviewed", message, preview)
    return "Preview ready: mark this transaction as reviewed.", audit, preview


def _preview_link_friend(db: Session, user_id: int, message: str, unlink: bool = False) -> tuple[str, AiActionAudit | None, dict]:
    transaction_id = _extract_transaction_id(message)
    friend_name = _extract_keyword(message)
    friend = db.query(Friend).filter(Friend.user_id == user_id, Friend.normalized_name.ilike(f"%{normalize_friend_name(friend_name)}%"), Friend.is_archived == False).first() if friend_name else None  # noqa: E712
    if not unlink and not friend:
        return "Tell me which friend to link, for example: Link transaction 42 to friend Ali.", None, {}
    rows = []
    if transaction_id:
        row = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.id == transaction_id).first()
        rows = [row] if row else []
    elif friend:
        rows = _transactions_by_keyword(db, user_id, friend.name, limit=100)
    preview = {"friend_id": friend.id if friend else None, "friend_name": friend.name if friend else None, "transaction_ids": [row.id for row in rows], "matched_count": len(rows), "sample": [_serialize_transaction(row) for row in rows[:10]]}
    action = "unlink_transaction_from_friend" if unlink else "link_transaction_to_friend"
    audit = _audit_preview(db, user_id, action, message, preview)
    return f"Preview ready: {action.replace('_', ' ')} for {len(rows)} transaction(s).", audit, preview


def _preview_budget_or_goal(action_type: str, message: str, db: Session, user_id: int) -> tuple[str, AiActionAudit | None, dict]:
    preview = {"request": message, "note": "This action needs structured form fields before it can be safely applied."}
    audit = _audit_preview(db, user_id, action_type, message, preview)
    return "I can prepare this, but use the form for exact fields before saving.", audit, preview


def execute_confirmed_action(db: Session, user_id: int, audit_id: int, confirm: bool) -> dict:
    audit = db.query(AiActionAudit).filter(AiActionAudit.id == audit_id, AiActionAudit.user_id == user_id).first()
    if not audit:
        return {"status": "not_found", "message": "Pending action not found.", "result": None}
    if not confirm:
        audit.status = "cancelled"
        audit.confirmed_at = datetime.now()
        db.commit()
        return {"status": "cancelled", "message": "Action cancelled.", "result": None}

    preview = json.loads(audit.preview_payload or "{}")
    transaction_ids = preview.get("transaction_ids", [])
    result: dict[str, Any] = {}
    if audit.action_type in {"update_transaction_category", "bulk_update_transaction_category"}:
        updated = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.id.in_(transaction_ids))
            .update({"category_id": preview["category_id"], "category_confidence": 1.0, "categorization_method": "ai_confirmed", "is_needs_review": False}, synchronize_session=False)
        )
        result = {"updated_transactions": updated, "category_name": preview.get("category_name")}
    elif audit.action_type == "mark_transaction_reviewed":
        updated = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.id.in_(transaction_ids))
            .update({"is_needs_review": False, "review_reason": None}, synchronize_session=False)
        )
        result = {"reviewed_transactions": updated}
    elif audit.action_type == "link_transaction_to_friend":
        updated = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.id.in_(transaction_ids))
            .update({"friend_id": preview["friend_id"], "is_friend_transaction": True, "categorization_method": "friend_match", "category_confidence": 0.95}, synchronize_session=False)
        )
        result = {"linked_transactions": updated, "friend_name": preview.get("friend_name")}
    elif audit.action_type == "unlink_transaction_from_friend":
        updated = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.id.in_(transaction_ids))
            .update({"friend_id": None, "is_friend_transaction": False, "categorization_method": "manual"}, synchronize_session=False)
        )
        result = {"unlinked_transactions": updated}
    else:
        audit.status = "blocked"
        audit.error_message = "This preview-only action is not executable yet."
        db.commit()
        return {"status": "blocked", "message": audit.error_message, "result": preview}

    audit.status = "confirmed"
    audit.result_payload = json.dumps(result, default=str)
    audit.confirmed_at = datetime.now()
    db.commit()
    return {"status": "confirmed", "message": "Confirmed action completed.", "result": result}


def run_assistant(db: Session, user_id: int, message: str) -> dict[str, Any]:
    intent = detect_intent(message)
    if intent == "unsafe_sql_blocked":
        return _response("I cannot generate or run SQL. I can use safe finance tools instead.", intent, True, {})

    preview_handlers = {
        "update_transaction_category": lambda: _preview_update_category(db, user_id, message, False),
        "bulk_update_transaction_category": lambda: _preview_update_category(db, user_id, message, True),
        "mark_transaction_reviewed": lambda: _preview_mark_reviewed(db, user_id, message),
        "link_transaction_to_friend": lambda: _preview_link_friend(db, user_id, message, False),
        "unlink_transaction_from_friend": lambda: _preview_link_friend(db, user_id, message, True),
        "create_budget": lambda: _preview_budget_or_goal("create_budget", message, db, user_id),
        "update_budget": lambda: _preview_budget_or_goal("update_budget", message, db, user_id),
        "create_savings_goal": lambda: _preview_budget_or_goal("create_savings_goal", message, db, user_id),
        "update_savings_goal": lambda: _preview_budget_or_goal("update_savings_goal", message, db, user_id),
    }
    if intent in preview_handlers:
        text, audit, preview = preview_handlers[intent]()
        return _response(text, intent, False, None, audit, preview)

    tool_map = {
        "get_monthly_summary": lambda: get_monthly_summary(db, user_id),
        "get_spending_by_category": lambda: get_spending_by_category(db, user_id),
        "get_top_merchants": lambda: get_top_merchants(db, user_id),
        "search_transactions": lambda: search_transactions(db, user_id, message),
        "get_budget_status": lambda: get_budget_status(db, user_id),
        "get_savings_goals": lambda: get_savings_goals(db, user_id),
        "get_subscriptions": lambda: get_subscriptions(db, user_id),
        "get_friend_transactions": lambda: get_friend_transactions(db, user_id, message),
        "get_friend_sent_amount": lambda: get_friend_amount(db, user_id, message, "expense"),
        "get_friend_received_amount": lambda: get_friend_amount(db, user_id, message, "income"),
        "detect_unusual_spending": lambda: detect_unusual_spending(db, user_id),
        "compare_months": lambda: compare_months(db, user_id),
    }
    data = tool_map.get(intent, tool_map["get_monthly_summary"])()
    return _response(summarize_tool_result(intent, data), intent, True, data)


def _response(message: str, intent: str, read_only: bool, data: dict | None, audit: AiActionAudit | None = None, preview: dict | None = None) -> dict[str, Any]:
    return {
        "message": message,
        "intent": intent,
        "read_only": read_only,
        "data": data,
        "pending_action": {
            "audit_id": audit.id,
            "action_type": audit.action_type,
            "explanation": "This change will run only after you confirm it.",
            "preview": preview or {},
            "requires_confirmation": True,
        } if audit else None,
        "suggested_questions": [
            "How much did I spend this month?",
            "Show my top merchants this month",
            "Which categories are over budget?",
            "Search transactions for Zomato",
        ],
    }


def summarize_tool_result(intent: str, data: dict) -> str:
    if intent == "get_monthly_summary":
        return f"This month: income INR {data['income']:.2f}, expenses INR {data['expenses']:.2f}, savings INR {data['savings']:.2f}."
    if intent == "search_transactions":
        return f"I found {len(data['transactions'])} matching transactions."
    if intent == "get_spending_by_category":
        return f"I found spending across {len(data['categories'])} categories."
    if intent == "get_top_merchants":
        return f"I found {len(data['merchants'])} top merchants."
    if intent == "get_budget_status":
        return f"You have {len(data['budgets'])} active budgets."
    if intent == "get_savings_goals":
        return f"You have {len(data['goals'])} savings goals."
    if intent == "get_subscriptions":
        return f"I found {data['subscription_count']} active subscriptions totaling INR {data['monthly_total']:.2f} per month."
    if intent == "get_friend_transactions":
        return f"I found {len(data['transactions'])} transactions with {data.get('friend') or 'that friend'}."
    if intent in {"get_friend_sent_amount", "get_friend_received_amount"}:
        direction = "sent" if intent == "get_friend_sent_amount" else "received"
        return f"You {direction} INR {data['total']:.2f} across {len(data['transactions'])} transactions with {data.get('friend') or 'that friend'}."
    if intent == "detect_unusual_spending":
        return f"I found {len(data['transactions'])} high-value transactions to review."
    if intent == "compare_months":
        return f"Current expenses differ from last month by INR {data['difference']:.2f}."
    return "I found the requested finance data."
