from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.services.transaction_cleaner_service import map_column_name, standardize_transaction


def _read_dataframe(file_name: str, content: bytes) -> pd.DataFrame:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(BytesIO(content))
    return pd.read_excel(BytesIO(content))


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in record.items():
        standard_key = map_column_name(key)
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

    for index, record in enumerate(dataframe.to_dict(orient="records"), start=1):
        transaction, failed_item = standardize_transaction(
            _normalize_record(record),
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
    }
