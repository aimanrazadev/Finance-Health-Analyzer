import unittest
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.file_parser_service import parse_statement_file, validate_statement_file
from app.services.pdf_parser_service import _extract_rows_from_tables


class PDFUploadTests(unittest.TestCase):
    def test_validation_accepts_pdf_extension_and_signature(self):
        content = b"%PDF-1.7\nstatement"
        validate_statement_file("bank-statement.pdf", len(content), content)

    def test_validation_rejects_other_extensions(self):
        with self.assertRaises(HTTPException) as context:
            validate_statement_file("bank-statement.txt", 100)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("PDF", context.exception.detail)

    def test_validation_rejects_invalid_pdf_content(self):
        content = b"not a document"
        with self.assertRaises(HTTPException) as context:
            validate_statement_file("bank-statement.pdf", len(content), content)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("valid PDF", context.exception.detail)

    @patch("app.services.file_parser_service.parse_pdf_statement")
    def test_statement_parser_uses_pdf_pipeline(self, parse_pdf_statement):
        parse_pdf_statement.return_value = {
            "total_rows": 1,
            "transactions": [{"description": "Payment"}],
            "failed_items": [],
        }
        content = b"%PDF-1.7\nstatement"

        result = parse_statement_file("bank-statement.pdf", content, MagicMock(), user_id=7)

        parse_pdf_statement.assert_called_once_with(
            content,
            unittest.mock.ANY,
            user_id=7,
            file_name="bank-statement.pdf",
        )
        self.assertEqual(result["file_type"], "pdf")
        self.assertEqual(result["successful_rows"], 1)

    @patch("pdfplumber.open")
    def test_extracts_all_pages_and_merges_description_lines(self, pdf_open):
        first_page = MagicMock()
        first_page.extract_tables.return_value = [[
            ["Date", "Description", "Reference No", "Withdrawal", "Deposit", "Balance"],
            ["01 Mar 2026", "Card payment", "REF-1", "1,200.00", "", "8,800.00"],
            ["", "continued merchant name", "", "", "", ""],
        ]]
        second_page = MagicMock()
        second_page.extract_tables.return_value = [[
            ["Date", "Description", "Reference No", "Withdrawal", "Deposit", "Balance"],
            ["02 Mar 2026", "Salary", "REF-2", "", "12,000.00", "20,800.00"],
        ]]
        pdf_open.return_value.__enter__.return_value.pages = [first_page, second_page]

        rows, columns = _extract_rows_from_tables(b"%PDF-1.7")

        self.assertEqual(len(rows), 2)
        self.assertEqual(columns[0], "Date")
        self.assertEqual(rows[0]["description"], "Card payment continued merchant name")
        self.assertEqual(rows[1]["deposit_amount"], "12,000.00")


if __name__ == "__main__":
    unittest.main()
