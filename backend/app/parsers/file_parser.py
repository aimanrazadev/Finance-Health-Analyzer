from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.parsers.pdf_parser import parse_pdf_statement


SUPPORTED_EXTENSION = ".pdf"
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


def detect_file_type(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix == SUPPORTED_EXTENSION:
        return "pdf"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Upload a PDF bank statement.",
    )


def validate_statement_file(file_name: str, file_size: int, content: bytes | None = None) -> None:
    if Path(file_name).suffix.lower() != SUPPORTED_EXTENSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload a PDF bank statement.",
        )
    if file_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size must be 10 MB or less.")
    if content is not None and not content.lstrip().startswith(b"%PDF-"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The selected file is not a valid PDF.")


def parse_statement_file(
    file_name: str,
    content: bytes,
    db: Session,
    user_id: int | None = None,
) -> dict[str, Any]:
    validate_statement_file(file_name, len(content), content)
    file_type = detect_file_type(file_name)

    try:
        parsed = parse_pdf_statement(content, db, user_id=user_id, file_name=file_name)
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
        "opening_balance": parsed.get("opening_balance"),
        "closing_balance": parsed.get("closing_balance"),
        "total_rows": total_rows,
        "successful_rows": len(transactions),
        "failed_rows": len(failed_items),
        "transactions": transactions,
        "failed_items": failed_items,
        "import_profile": parsed.get("import_profile") or {
            "id": None,
            "name": None,
            "confidence": 1.0,
            "column_mapping": {},
            "bank_name": None,
            "columns": [],
        },
    }
