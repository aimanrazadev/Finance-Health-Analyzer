import unittest
from datetime import datetime

from pydantic import ValidationError

from app.schemas.schemas import TransactionCreate
from app.services.category_service import DEFAULT_CATEGORY_DEFINITIONS
from app.services.transaction_type_service import normalize_transaction_type


class TransactionTypeTests(unittest.TestCase):
    def test_only_income_and_expense_are_valid_types(self):
        self.assertEqual(normalize_transaction_type(None, "income", None), "income")
        self.assertEqual(normalize_transaction_type(None, "expense", None), "expense")
        self.assertEqual(normalize_transaction_type(None, "other", None), "expense")

    def test_savings_is_a_category_not_a_transaction_type(self):
        category_names = {category["name"] for category in DEFAULT_CATEGORY_DEFINITIONS}
        self.assertIn("Savings", category_names)

        with self.assertRaises(ValidationError):
            TransactionCreate(
                amount=100,
                description="Transfer to reserve",
                transaction_type="savings",
                date=datetime.now(),
            )


if __name__ == "__main__":
    unittest.main()
