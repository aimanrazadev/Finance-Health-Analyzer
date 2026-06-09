from io import BytesIO
import re
from typing import Any

from sqlalchemy.orm import Session

from services.transaction_cleaner_service import map_column_name, standardize_transaction


HEADER_KEYWORDS = ("date", "description", "withdrawal", "deposit", "balance")
TRANSACTION_START_RE = re.compile(r"^\s*(?P<number>\d+)\s+(?P<date>\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(?P<body>.+)$")
AMOUNT_RE = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?")
REFERENCE_RE = re.compile(r"\b(?:UPI|MB|FOS|IMPS|NEFT|RTGS|ACH|NACH)[-/A-Z0-9]*\b", re.IGNORECASE)
INCOME_HINT_RE = re.compile(r"\b(received|salary|deposit|credit|refund|cr|monthly expenses)\b", re.IGNORECASE)


def _cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _looks_like_header(row: list[Any]) -> bool:
    text = " ".join(_cell(cell).lower() for cell in row)
    return "date" in text and ("description" in text or "particular" in text) and "balance" in text


def _is_noise(text: str) -> bool:
    lowered = text.lower()
    noise_terms = (
        "account statement",
        "account details",
        "address",
        "opening balance",
        "statement generated",
        "page ",
        "computer generated",
    )
    return not text.strip() or any(term in lowered for term in noise_terms)


def _merge_continuation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for row in rows:
        if row.get("transaction_date"):
            merged.append(row)
            continue

        if merged:
            extra_text = " ".join(
                str(row.get(key) or "").strip()
                for key in ("description", "reference_no")
                if str(row.get(key) or "").strip()
            )
            if extra_text:
                merged[-1]["description"] = f"{merged[-1].get('description', '')} {extra_text}".strip()

    return merged


def _extract_rows_from_tables(content: bytes) -> list[dict[str, Any]]:
    import pdfplumber

    raw_rows: list[dict[str, Any]] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                header: list[str] | None = None
                for row in table:
                    if not row:
                        continue
                    if header is None:
                        if _looks_like_header(row):
                            header = [map_column_name(_cell(cell)) for cell in row]
                        continue

                    record = {
                        header[index]: _cell(value)
                        for index, value in enumerate(row)
                        if index < len(header) and header[index]
                    }
                    if record and not _is_noise(" ".join(str(value) for value in record.values())):
                        raw_rows.append(record)

    return _merge_continuation_rows(raw_rows)


def _extract_text_lines(content: bytes) -> list[str]:
    import pdfplumber

    lines: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(line.strip() for line in text.splitlines() if line.strip())
    return lines


def _record_from_text_match(match: re.Match[str]) -> dict[str, Any] | None:
    body = match.group("body").strip()
    if _is_noise(body):
        return None

    amounts = list(AMOUNT_RE.finditer(body))
    if len(amounts) < 2:
        return None

    balance = amounts[-1].group(0)
    transaction_amount = amounts[-2].group(0)
    description = body[: amounts[-2].start()].strip(" -|")
    reference_match = REFERENCE_RE.search(description)
    reference_no = reference_match.group(0) if reference_match else None
    is_income = bool(INCOME_HINT_RE.search(body))

    return {
        "transaction_date": match.group("date"),
        "description": description,
        "reference_no": reference_no,
        "withdrawal_amount": None if is_income else transaction_amount,
        "deposit_amount": transaction_amount if is_income else None,
        "balance": balance,
    }


def _extract_rows_from_text(content: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    found_header = False

    for line in _extract_text_lines(content):
        lowered = line.lower()
        if not found_header:
            found_header = "date" in lowered and "description" in lowered and "balance" in lowered
            continue
        if _is_noise(line):
            continue

        match = TRANSACTION_START_RE.match(line)
        if match:
            record = _record_from_text_match(match)
            if record:
                rows.append(record)
            continue

        if rows:
            rows[-1]["description"] = f"{rows[-1].get('description', '')} {line}".strip()

    return rows


def parse_pdf_statement(content: bytes, db: Session, user_id: int | None = None) -> dict[str, Any]:
    raw_rows = _extract_rows_from_tables(content)
    if not raw_rows:
        raw_rows = _extract_rows_from_text(content)

    transactions: list[dict[str, Any]] = []
    failed_items: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows, start=1):
        transaction, failed_item = standardize_transaction(
            raw,
            source="pdf",
            row_number=index,
            db=db,
            user_id=user_id,
        )
        if transaction:
            transactions.append(transaction)
        elif failed_item:
            failed_items.append(failed_item)

    return {
        "total_rows": len(raw_rows),
        "transactions": transactions,
        "failed_items": failed_items,
    }
