import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import ImportProfile
from app.services.transaction_cleaner_service import map_column_name


REQUIRED_FIELDS = {"date", "description"}
AMOUNT_FIELDS = {"amount", "withdrawal_amount", "deposit_amount"}


def infer_bank_name(file_name: str) -> str:
    """Use the filename as a practical bank/profile hint for student-project imports."""
    stem = Path(file_name or "statement").stem
    cleaned = re.sub(r"[_-]+", " ", stem)
    cleaned = re.sub(r"\b(statement|transactions|account|bank|pdf)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() or "Unknown Bank"


def build_header_signature(columns: list[str]) -> str:
    """Stable fingerprint for a statement layout."""
    normalized = [re.sub(r"\s+", " ", str(column).strip().lower()) for column in columns]
    return "|".join(sorted(normalized))


def infer_column_mapping(columns: list[str]) -> dict[str, str]:
    return {str(column): map_column_name(str(column)) for column in columns}


def calculate_mapping_confidence(mapping: dict[str, str]) -> float:
    mapped_values = set(mapping.values())
    score = 0.0
    if REQUIRED_FIELDS.issubset(mapped_values):
        score += 0.55
    else:
        score += 0.20 * len(REQUIRED_FIELDS.intersection(mapped_values))
    if mapped_values & AMOUNT_FIELDS:
        score += 0.35
    if "balance" in mapped_values:
        score += 0.10
    return round(min(score, 1.0), 2)


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def serialize_import_profile(profile: ImportProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "profile_name": profile.profile_name,
        "bank_name": profile.bank_name,
        "file_type": profile.file_type,
        "header_signature": profile.header_signature,
        "column_mapping": _loads(profile.column_mapping, {}),
        "preferences": _loads(profile.preferences, {}),
        "confidence_score": profile.confidence_score or 0,
        "usage_count": profile.usage_count or 0,
        "last_used_at": profile.last_used_at,
        "created_at": profile.created_at,
    }


def find_matching_import_profile(
    db: Session,
    user_id: int,
    file_name: str,
    file_type: str,
    columns: list[str],
) -> ImportProfile | None:
    signature = build_header_signature(columns)
    bank_name = infer_bank_name(file_name)
    return (
        db.query(ImportProfile)
        .filter(
            ImportProfile.user_id == user_id,
            ImportProfile.file_type == file_type,
            (
                (ImportProfile.header_signature == signature)
                | (ImportProfile.bank_name == bank_name)
            ),
        )
        .order_by(ImportProfile.header_signature.desc(), ImportProfile.usage_count.desc())
        .first()
    )


def resolve_import_mapping(
    db: Session,
    user_id: int | None,
    file_name: str,
    file_type: str,
    columns: list[str],
) -> dict[str, Any]:
    inferred = infer_column_mapping(columns)
    profile = find_matching_import_profile(db, user_id, file_name, file_type, columns) if user_id else None
    mapping = _loads(profile.column_mapping, inferred) if profile else inferred
    confidence = profile.confidence_score if profile else calculate_mapping_confidence(mapping)
    return {
        "profile": profile,
        "mapping": mapping,
        "confidence": round(float(confidence or 0), 2),
        "bank_name": profile.bank_name if profile else infer_bank_name(file_name),
        "header_signature": build_header_signature(columns),
    }


def save_import_profile_from_columns(
    db: Session,
    user_id: int,
    file_name: str,
    file_type: str,
    columns: list[str],
    preferences: dict[str, Any] | None = None,
) -> ImportProfile:
    context = resolve_import_mapping(db, user_id, file_name, file_type, columns)
    profile = context["profile"]
    if not profile:
        profile = ImportProfile(
            user_id=user_id,
            profile_name=f"{context['bank_name']} {file_type.upper()} profile",
            bank_name=context["bank_name"],
            file_type=file_type,
            header_signature=context["header_signature"],
        )
        db.add(profile)

    profile.column_mapping = json.dumps(context["mapping"], ensure_ascii=True)
    profile.preferences = json.dumps(preferences or {}, ensure_ascii=True)
    profile.confidence_score = context["confidence"]
    profile.usage_count = int(profile.usage_count or 0) + 1
    profile.last_used_at = datetime.utcnow()
    db.flush()
    return profile
