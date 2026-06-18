import json
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Merchant, Transaction
from app.services.merchant_extractor_service import extract_transaction_merchant, normalize_merchant_name


def _loads_aliases(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _dump_aliases(aliases: list[str]) -> str:
    cleaned = sorted({alias.strip() for alias in aliases if alias and alias.strip()})
    return json.dumps(cleaned, ensure_ascii=True)


def serialize_merchant(merchant: Merchant) -> dict[str, Any]:
    return {
        "id": merchant.id,
        "user_id": merchant.user_id,
        "canonical_name": merchant.canonical_name,
        "normalized_name": merchant.normalized_name,
        "aliases": _loads_aliases(merchant.aliases),
        "transaction_count": merchant.transaction_count or 0,
        "total_spent": merchant.total_spent or 0,
        "last_seen_at": merchant.last_seen_at,
    }


def get_or_create_merchant(db: Session, user_id: int, merchant_name: str | None) -> Merchant | None:
    display_name = extract_transaction_merchant(merchant_name, merchant_name)
    normalized = normalize_merchant_name(display_name)
    if not normalized:
        return None

    merchant = (
        db.query(Merchant)
        .filter(Merchant.user_id == user_id, Merchant.normalized_name == normalized)
        .first()
    )
    if not merchant:
        merchant = Merchant(
            user_id=user_id,
            canonical_name=display_name or normalized.title(),
            normalized_name=normalized,
            aliases=_dump_aliases([display_name or normalized.title()]),
        )
        db.add(merchant)
        db.flush()
    return merchant


def refresh_merchant_stats(db: Session, user_id: int) -> None:
    merchants = db.query(Merchant).filter(Merchant.user_id == user_id).all()
    for merchant in merchants:
        rows = (
            db.query(
                func.count(Transaction.id).label("count"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                func.max(Transaction.date).label("last_seen"),
            )
            .filter(Transaction.user_id == user_id, Transaction.merchant_id == merchant.id)
            .first()
        )
        merchant.transaction_count = int(rows.count or 0)
        merchant.total_spent = round(float(rows.total or 0), 2)
        merchant.last_seen_at = rows.last_seen


def sync_merchants_from_transactions(db: Session, user_id: int) -> list[Merchant]:
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc())
        .all()
    )
    for transaction in transactions:
        merchant_name = extract_transaction_merchant(
            transaction.description,
            transaction.extracted_merchant or transaction.merchant,
        )
        if not merchant_name:
            continue
        merchant = get_or_create_merchant(db, user_id, merchant_name)
        if merchant:
            aliases = _loads_aliases(merchant.aliases)
            merchant.aliases = _dump_aliases([*aliases, merchant_name, transaction.merchant or ""])
            transaction.merchant_id = merchant.id
            transaction.merchant = merchant.canonical_name
            transaction.extracted_merchant = merchant.canonical_name
    refresh_merchant_stats(db, user_id)
    db.commit()
    return db.query(Merchant).filter(Merchant.user_id == user_id).order_by(Merchant.total_spent.desc()).all()


def rename_merchant(db: Session, user_id: int, merchant_id: int, canonical_name: str) -> Merchant | None:
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id, Merchant.user_id == user_id).first()
    if not merchant:
        return None
    old_name = merchant.canonical_name
    merchant.canonical_name = canonical_name.strip()
    merchant.normalized_name = normalize_merchant_name(canonical_name)
    merchant.aliases = _dump_aliases([*_loads_aliases(merchant.aliases), old_name, canonical_name])
    db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.merchant_id == merchant.id).update(
        {
            Transaction.merchant: merchant.canonical_name,
            Transaction.extracted_merchant: merchant.canonical_name,
        },
        synchronize_session=False,
    )
    merchant.updated_at = datetime.utcnow()
    refresh_merchant_stats(db, user_id)
    db.commit()
    db.refresh(merchant)
    return merchant


def merge_merchants(db: Session, user_id: int, target_id: int, source_id: int) -> Merchant | None:
    target = db.query(Merchant).filter(Merchant.id == target_id, Merchant.user_id == user_id).first()
    source = db.query(Merchant).filter(Merchant.id == source_id, Merchant.user_id == user_id).first()
    if not target or not source or target.id == source.id:
        return None

    aliases = [*_loads_aliases(target.aliases), *_loads_aliases(source.aliases), source.canonical_name]
    target.aliases = _dump_aliases(aliases)
    db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.merchant_id == source.id).update(
        {
            Transaction.merchant_id: target.id,
            Transaction.merchant: target.canonical_name,
            Transaction.extracted_merchant: target.canonical_name,
        },
        synchronize_session=False,
    )
    db.delete(source)
    refresh_merchant_stats(db, user_id)
    db.commit()
    db.refresh(target)
    return target


def merchant_detail(db: Session, user_id: int, merchant_id: int) -> dict[str, Any] | None:
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id, Merchant.user_id == user_id).first()
    if not merchant:
        return None
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.merchant_id == merchant.id)
        .order_by(Transaction.date.desc())
        .limit(50)
        .all()
    )
    total_income = round(sum(row.amount for row in transactions if row.transaction_type == "income"), 2)
    total_expenses = round(sum(row.amount for row in transactions if row.transaction_type == "expense"), 2)
    return {
        "merchant": serialize_merchant(merchant),
        "total_income": total_income,
        "total_expenses": total_expenses,
        "transaction_count": len(transactions),
        "average_amount": round((total_income + total_expenses) / len(transactions), 2) if transactions else 0,
        "transactions": transactions,
    }
