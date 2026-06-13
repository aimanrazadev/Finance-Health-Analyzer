import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.uploads import _duplicate_exists
from app.db.database import Base
from app.models.models import Category, Transaction
from app.schemas.schemas import UploadPreviewRow
from app.services.category_service import seed_default_categories
from app.services.file_parser_service import parse_statement_file


class UploadAndTransactionTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()
        seed_default_categories(self.session)

    def tearDown(self):
        self.session.close()

    def category_id(self, name):
        category = self.session.query(Category).filter(Category.name == name).one()
        return category.id

    def test_pdf_upload_preview_parses_pdf_rows_and_failed_rows(self):
        raw_pdf_rows = [
            {
                "transaction_date": "01 Mar 2026",
                "description": "UPI/SWIGGY/ORDER123",
                "reference_no": "UPI-123",
                "withdrawal_amount": "1,250.50",
                "deposit_amount": "",
                "balance": "12,000.00",
            },
            {
                "transaction_date": "02 Mar 2026",
                "description": "Salary credit March",
                "reference_no": "NEFT-SALARY",
                "withdrawal_amount": "",
                "deposit_amount": "50,000.00",
                "balance": "62,000.00",
            },
            {
                "transaction_date": "03 Mar 2026",
                "description": "",
                "withdrawal_amount": "10.00",
                "balance": "61,990.00",
            },
        ]

        with patch("app.services.pdf_parser_service._extract_rows_from_tables", return_value=raw_pdf_rows):
            result = parse_statement_file("kotak_statement.pdf", b"%PDF-1.4 fake bytes", self.session, user_id=1)

        self.assertEqual(result["file_type"], "pdf")
        self.assertEqual(result["total_rows"], 3)
        self.assertEqual(result["successful_rows"], 2)
        self.assertEqual(result["failed_rows"], 1)

        food_row = result["transactions"][0]
        self.assertEqual(food_row["source"], "pdf")
        self.assertEqual(food_row["amount"], 1250.50)
        self.assertEqual(food_row["transaction_type"], "expense")
        self.assertEqual(food_row["category_id"], self.category_id("Food"))

        salary_row = result["transactions"][1]
        self.assertEqual(salary_row["amount"], 50000.00)
        self.assertEqual(salary_row["transaction_type"], "income")
        self.assertEqual(salary_row["category_id"], self.category_id("Salary"))
        self.assertIn("description is missing", result["failed_items"][0]["error"])

    def test_import_duplicate_detection_uses_user_date_amount_description_and_reference(self):
        date = datetime(2026, 3, 1)
        self.session.add(
            Transaction(
                user_id=1,
                amount=1250.50,
                category_id=self.category_id("Food"),
                description="UPI/SWIGGY/ORDER123",
                merchant="SWIGGY",
                reference_no="UPI-123",
                transaction_type="expense",
                date=date,
                source="pdf",
            )
        )
        self.session.commit()

        duplicate_row = UploadPreviewRow(
            row_number=1,
            transaction_date=date,
            date=date,
            description="UPI/SWIGGY/ORDER123",
            reference_no="UPI-123",
            amount=1250.50,
            transaction_type="expense",
            source="pdf",
        )
        different_user_row = duplicate_row.model_copy()

        self.assertTrue(_duplicate_exists(self.session, 1, duplicate_row))
        self.assertFalse(_duplicate_exists(self.session, 2, different_user_row))


if __name__ == "__main__":
    unittest.main()
