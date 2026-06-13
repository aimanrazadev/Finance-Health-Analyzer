from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Category
from app.services.categorization import get_predicted_category_id

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

DATE_COLUMNS = ["date", "transaction_date", "posted_date", "value_date"]
DESCRIPTION_COLUMNS = ["description", "details", "narration", "transaction", "memo"]
AMOUNT_COLUMNS = ["amount", "value", "transaction_amount"]
TYPE_COLUMNS = ["type", "transaction_type", "debit_credit"]
MERCHANT_COLUMNS = ["merchant", "merchant_name", "payee", "vendor"]


def validate_upload_file(file_name: str, file_size: int) -> str:
    extension = Path(file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are supported.",
        )

    if file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be 5 MB or less.",
        )

    return extension


def read_statement_file(file_name: str, content: bytes) -> pd.DataFrame:
    extension = validate_upload_file(file_name, len(content))
    buffer = BytesIO(content)

    try:
        if extension == ".csv":
            return pd.read_csv(buffer)
        return pd.read_excel(buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read statement file. Check that it is a valid CSV or Excel file.",
        ) from exc


def normalize_column_name(column: Any) -> str:
    return str(column).strip().lower().replace(" ", "_").replace("-", "_")


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def get_required_columns(df: pd.DataFrame) -> tuple[str, str, str, str | None, str | None]:
    normalized_columns = [normalize_column_name(column) for column in df.columns]
    df.columns = normalized_columns

    date_column = find_column(normalized_columns, DATE_COLUMNS)
    description_column = find_column(normalized_columns, DESCRIPTION_COLUMNS)
    amount_column = find_column(normalized_columns, AMOUNT_COLUMNS)
    type_column = find_column(normalized_columns, TYPE_COLUMNS)
    merchant_column = find_column(normalized_columns, MERCHANT_COLUMNS)

    missing = []
    if not date_column:
        missing.append("date")
    if not description_column:
        missing.append("description")
    if not amount_column:
        missing.append("amount")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required column(s): {', '.join(missing)}.",
        )

    return date_column, description_column, amount_column, type_column, merchant_column


def clean_amount(value: Any) -> float:
    text_value = (
        str(value)
        .replace(",", "")
        .replace("SAR", "")
        .replace("INR", "")
        .replace("?", "")
        .strip()
    )
    if text_value.startswith("(") and text_value.endswith(")"):
        text_value = f"-{text_value[1:-1]}"
    return float(text_value)


def detect_transaction_type(amount: float, raw_type: Any = None) -> str:
    type_text = str(raw_type or "").strip().lower()
    if type_text in {"income", "credit", "cr", "deposit"}:
        return "income"
    if type_text in {"expense", "debit", "dr", "withdrawal"}:
        return "expense"
    return "income" if amount > 0 else "expense"


def parse_statement_rows(db: Session, file_name: str, content: bytes) -> dict:
    df = read_statement_file(file_name, content)
    date_column, description_column, amount_column, type_column, merchant_column = get_required_columns(df)

    rows = []
    errors = []

    for index, record in df.iterrows():
        row_number = int(index) + 2
        try:
            parsed_date = pd.to_datetime(record[date_column], errors="raise").to_pydatetime()
            raw_amount = clean_amount(record[amount_column])
            transaction_type = detect_transaction_type(
                raw_amount,
                record[type_column] if type_column else None,
            )
            description = str(record[description_column]).strip()
            merchant = str(record[merchant_column]).strip() if merchant_column and pd.notna(record[merchant_column]) else None

            if not description:
                raise ValueError("description is empty")

            category_id = get_predicted_category_id(db, description, merchant)
            category_name = None
            if category_id:
                predicted_category = db.query(Category).filter(Category.id == category_id).first()
                category_name = predicted_category.name if predicted_category else None

            rows.append(
                {
                    "row_number": row_number,
                    "date": parsed_date,
                    "description": description,
                    "amount": abs(raw_amount),
                    "transaction_type": transaction_type,
                    "merchant": merchant,
                    "category_id": category_id,
                    "category_name": category_name,
                }
            )
        except Exception as exc:
            errors.append(f"Row {row_number}: {exc}")

    return {
        "file_name": file_name,
        "file_size": len(content),
        "file_type": Path(file_name).suffix.lower().replace(".", ""),
        "total_rows": int(len(df.index)),
        "valid_rows": len(rows),
        "failed_rows": len(errors),
        "rows": rows,
        "errors": errors,
    }
