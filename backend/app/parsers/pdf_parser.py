from io import BytesIO
import re
from typing import Any

from sqlalchemy.orm import Session

from app.parsers.transaction_cleaner import map_column_name, standardize_transaction


TRANSACTION_START_RE = re.compile(r"^\s*(?P<number>\d+)\s+(?P<date>\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(?P<body>.+)$")
TRANSACTION_DATE_RE = re.compile(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$")
AMOUNT_RE = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?")
REFERENCE_RE = re.compile(r"\b(?:UPI|MB|FOS|IMPS|NEFT|RTGS|ACH|NACH)[-/A-Z0-9]*\b", re.IGNORECASE)
INCOME_HINT_RE = re.compile(r"\b(received|salary|deposit|credit|refund|cr|monthly expenses)\b", re.IGNORECASE)
OPENING_BALANCE_RE = re.compile(
    r"opening\s+balance\s*(?:[:=-]\s*)?(?:inr|rs\.?|₹)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
CLOSING_BALANCE_RE = re.compile(
    r"closing\s+balance\s*(?:[:=-]\s*)?(?:inr|rs\.?|â‚¹)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
# Currency symbols extracted from PDFs are not consistently Unicode-decoded,
# so accept any non-numeric prefix between the label and amount.
OPENING_BALANCE_RE = re.compile(
    r"opening\s+balance\s*(?:[:=-]\s*)?[^0-9\r\n]*([0-9][0-9,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
CLOSING_BALANCE_RE = re.compile(
    r"closing\s+balance\s*(?:[:=-]\s*)?[^0-9\r\n]*([0-9][0-9,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


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


def _extract_rows_from_tables(content: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    import pdfplumber

    raw_rows: list[dict[str, Any]] = []
    detected_columns: list[str] = []
    transaction_header: list[str | None] | None = None
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    if not row:
                        continue
                    if _looks_like_header(row):
                        source_header = [_cell(cell) for cell in row]
                        transaction_header = [map_column_name(cell) for cell in source_header]
                        if not detected_columns:
                            detected_columns = source_header
                        continue

                    # PDF extractors frequently split one visual ledger into
                    # multiple tables or pages. Continuation chunks do not
                    # repeat their header, so retain the last transaction
                    # header instead of silently discarding those rows.
                    if transaction_header is None:
                        continue

                    record = {
                        transaction_header[index]: _cell(value)
                        for index, value in enumerate(row)
                        if index < len(transaction_header) and transaction_header[index]
                    }
                    has_transaction_date = bool(
                        TRANSACTION_DATE_RE.fullmatch(str(record.get("transaction_date") or "").strip())
                    )
                    is_transaction_or_continuation = has_transaction_date or any(
                        record.get(key) for key in ("description", "reference_no")
                    )
                    if record and is_transaction_or_continuation and not _is_noise(" ".join(str(value) for value in record.values())):
                        raw_rows.append(record)

    return _merge_continuation_rows(raw_rows), detected_columns


def _extract_text_lines(content: bytes) -> list[str]:
    import pdfplumber

    lines: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(line.strip() for line in text.splitlines() if line.strip())
    return lines


def _extract_opening_balance(content: bytes) -> float | None:
    """Read the statement-level opening balance from Account Summary text."""
    for line in _extract_text_lines(content):
        match = OPENING_BALANCE_RE.search(line)
        if match:
            return round(float(match.group(1).replace(",", "")), 2)
    return None


def _extract_closing_balance(content: bytes) -> float | None:
    """Read the authoritative statement closing balance from Account Summary text."""
    lines = _extract_text_lines(content)
    for line in lines:
        match = CLOSING_BALANCE_RE.search(line)
        if match:
            return round(float(match.group(1).replace(",", "")), 2)

    # Some banks render the two labels as a header and put both values on the
    # following account row: "Opening Balance Closing Balance" then
    # "Savings Account: 399.08 5,359.96".
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "opening balance" not in lowered or "closing balance" not in lowered:
            continue
        for value_line in lines[index + 1:index + 4]:
            amounts = AMOUNT_RE.findall(value_line)
            if len(amounts) >= 2:
                return round(float(amounts[-1].replace(",", "")), 2)
    return None


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


def parse_pdf_statement(
    content: bytes,
    db: Session,
    user_id: int | None = None,
    file_name: str = "statement.pdf",
) -> dict[str, Any]:
    opening_balance = _extract_opening_balance(content)
    closing_balance = _extract_closing_balance(content)
    raw_rows, columns = _extract_rows_from_tables(content)
    if not raw_rows:
        raw_rows = _extract_rows_from_text(content)
        columns = ["Date", "Description", "Reference No", "Withdrawal", "Deposit", "Balance"]

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
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "transactions": transactions,
        "failed_items": failed_items,
    }
