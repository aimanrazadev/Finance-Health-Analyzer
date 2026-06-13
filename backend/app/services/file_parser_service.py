from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.csv_excel_parser_service import parse_csv_excel_statement
from app.services.pdf_parser_service import parse_pdf_statement


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


def detect_file_type(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".xlsx", ".xls"}:
        return "excel"
    if suffix == ".pdf":
        return "pdf"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Upload a CSV, Excel, or PDF statement.",
    )


def validate_statement_file(file_name: str, file_size: int) -> None:
    if Path(file_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload a CSV, Excel, or PDF statement.",
        )
    if file_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size must be 10 MB or less.")


def parse_statement_file(
    file_name: str,
    content: bytes,
    db: Session,
    user_id: int | None = None,
) -> dict[str, Any]:
    validate_statement_file(file_name, len(content))
    file_type = detect_file_type(file_name)

    try:
        if file_type == "pdf":
            parsed = parse_pdf_statement(content, db, user_id=user_id)
        else:
            parsed = parse_csv_excel_statement(file_name, content, file_type, db, user_id=user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse statement file: {exc}",
        ) from exc

    transactions = parsed.get("transactions", [])
    failed_items = parsed.get("failed_items", [])
    total_rows = parsed.get("total_rows", len(transactions) + len(failed_items))

    return {
        "file_type": file_type,
        "total_rows": total_rows,
        "successful_rows": len(transactions),
        "failed_rows": len(failed_items),
        "transactions": transactions,
        "failed_items": failed_items,
    }
