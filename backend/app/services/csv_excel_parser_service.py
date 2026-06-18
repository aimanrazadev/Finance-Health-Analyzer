from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.services.transaction_cleaner_service import map_column_name, standardize_transaction
from app.services.import_profile_service import resolve_import_mapping


def _read_dataframe(file_name: str, content: bytes) -> pd.DataFrame:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(BytesIO(content))
    return pd.read_excel(BytesIO(content))


def _normalize_record(record: dict[str, Any], column_mapping: dict[str, str] | None = None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in record.items():
        standard_key = (column_mapping or {}).get(str(key)) or map_column_name(key)
        normalized[standard_key] = value
    return normalized


def parse_csv_excel_statement(
    file_name: str,
    content: bytes,
    source: str,
    db: Session,
    user_id: int | None = None,
) -> dict[str, Any]:
    dataframe = _read_dataframe(file_name, content).dropna(how="all")
    transactions: list[dict[str, Any]] = []
    failed_items: list[dict[str, Any]] = []
    columns = [str(column) for column in dataframe.columns]
    profile_context = resolve_import_mapping(db, user_id, file_name, source, columns)

    for index, record in enumerate(dataframe.to_dict(orient="records"), start=1):
        transaction, failed_item = standardize_transaction(
            _normalize_record(record, profile_context["mapping"]),
            source=source,
            row_number=index,
            db=db,
            user_id=user_id,
        )
        if transaction:
            transactions.append(transaction)
        elif failed_item:
            failed_items.append(failed_item)

    return {
        "total_rows": len(dataframe.index),
        "transactions": transactions,
        "failed_items": failed_items,
        "import_profile": {
            "id": profile_context["profile"].id if profile_context["profile"] else None,
            "name": profile_context["profile"].profile_name if profile_context["profile"] else None,
            "confidence": profile_context["confidence"],
            "column_mapping": profile_context["mapping"],
            "bank_name": profile_context["bank_name"],
            "columns": columns,
        },
    }
