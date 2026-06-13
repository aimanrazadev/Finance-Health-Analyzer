import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import Category, CategoryLearningRule, Transaction
from app.services.categorization import categorize_transaction
from app.services.category_service import seed_default_categories
from app.services.learning_service import save_category_correction
from app.services.merchant_extractor_service import extract_merchant_name, normalize_merchant_name
from app.services.transaction_merchant_cleanup_service import clean_existing_transaction_merchants


class TransactionIntelligenceTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()
        seed_default_categories(self.session)

    def tearDown(self):
        self.session.close()

    def category_id(self, name):
        return self.session.query(Category).filter(Category.name == name).one().id

    def add_transaction(self, user_id, description, amount=100, transaction_type="expense"):
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            description=description,
            transaction_type=transaction_type,
            date=datetime(2026, 4, 1),
            category_confidence=0.30,
            categorization_method="needs_review",
            review_status="needs_review",
            is_needs_review=True,
        )
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def test_upi_merchant_extraction_matches_module_example(self):
        description = "UPI/RAJPAL/699380228491/Payment from Ph"

        self.assertEqual(extract_merchant_name(description), "Rajpal")
        self.assertEqual(normalize_merchant_name(description), "rajpal")

    def test_payment_rail_is_not_treated_as_merchant(self):
        self.assertEqual(
            extract_merchant_name("PCI/6820/OPENAI *CHATGPT SUBSCR/+14158030626/17:10"),
            "Openai",
        )
        self.assertEqual(
            extract_merchant_name("UPI/Go Grab/084397803030/Payment from Ph"),
            "Go Grab",
        )
        self.assertEqual(
            normalize_merchant_name("PCI/6820/OPENAI *CHATGPT SUBSCR/+14158030626/17:10"),
            "openai",
        )

    def test_cleanup_rewrites_old_upi_and_pci_merchants(self):
        old_rows = [
            Transaction(
                user_id=1,
                amount=20,
                description="UPI/Go Grab/084397803030/Payment from Ph",
                merchant="UPI",
                transaction_type="expense",
                date=datetime(2026, 4, 2),
            ),
            Transaction(
                user_id=1,
                amount=1999,
                description="PCI/6820/OPENAI *CHATGPT SUBSCR/+14158030626/17:10",
                merchant="PCI",
                transaction_type="expense",
                date=datetime(2026, 4, 3),
            ),
            Transaction(
                user_id=1,
                amount=1999,
                description="PCI/6820/OPENAI *CHATGPT SUBSCR/+14158030626/17:10",
                merchant="PCI/6820/OPENAI *CHATGPT SUBSCR/+14158030626/17:10",
                transaction_type="expense",
                date=datetime(2026, 4, 4),
            ),
        ]
        self.session.add_all(old_rows)
        self.session.commit()

        updated_count = clean_existing_transaction_merchants(self.session)

        self.assertEqual(updated_count, 3)
        self.assertEqual(self.session.get(Transaction, old_rows[0].id).merchant, "Go Grab")
        self.assertEqual(self.session.get(Transaction, old_rows[1].id).merchant, "Openai")
        self.assertEqual(self.session.get(Transaction, old_rows[2].id).merchant, "Openai")
        self.assertEqual(self.session.get(Transaction, old_rows[0].id).extracted_merchant, "Go Grab")

    def test_user_correction_creates_learned_rule_and_future_auto_categorization(self):
        transaction = self.add_transaction(1, "UPI/RAJPAL/699380228491/Payment from Ph")

        correction = save_category_correction(
            self.session,
            user_id=1,
            transaction_id=transaction.id,
            old_category_id=transaction.category_id,
            new_category_id=self.category_id("Food"),
        )
        self.session.commit()

        rule = self.session.query(CategoryLearningRule).filter(CategoryLearningRule.user_id == 1).one()
        result = categorize_transaction(
            self.session,
            user_id=1,
            description="UPI/RAJPAL/99887766/Payment from Ph",
            amount=200,
            transaction_type="expense",
        )

        self.assertEqual(correction.extracted_merchant, "Rajpal")
        self.assertEqual(rule.normalized_merchant, "rajpal")
        self.assertEqual(result["category_id"], self.category_id("Food"))
        self.assertEqual(result["method"], "learned")
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(result["review_status"], "approved")

    def test_user_specific_learning_rules_do_not_affect_other_users(self):
        transaction = self.add_transaction(1, "UPI/RAJPAL/699380228491/Payment from Ph")
        save_category_correction(self.session, 1, transaction.id, None, self.category_id("Food"))
        self.session.commit()

        result = categorize_transaction(
            self.session,
            user_id=2,
            description="UPI/RAJPAL/111/Payment from Ph",
            amount=200,
            transaction_type="expense",
        )

        self.assertNotEqual(result["method"], "learned")

    def test_rule_based_categorization_still_runs_after_learned_rules(self):
        result = categorize_transaction(
            self.session,
            user_id=1,
            description="Netflix monthly subscription",
            amount=499,
            transaction_type="expense",
        )

        self.assertEqual(result["category_id"], self.category_id("Subscriptions"))
        self.assertEqual(result["method"], "rule_based")
        self.assertEqual(result["review_status"], "approved")

    def test_ml_high_confidence_auto_assigns_after_no_learned_or_keyword_match(self):
        with patch("app.services.categorization.predict_category_with_ml", return_value=("Transport", 0.87)):
            result = categorize_transaction(
                self.session,
                user_id=1,
                description="Bluecar ride 32 SAR",
                amount=32,
                transaction_type="expense",
            )

        self.assertEqual(result["category_id"], self.category_id("Transport"))
        self.assertEqual(result["method"], "ml_model")
        self.assertEqual(result["confidence"], 0.87)
        self.assertEqual(result["review_status"], "approved")

    def test_ml_low_confidence_goes_to_needs_review(self):
        with patch("app.services.categorization.predict_category_with_ml", return_value=("Food", 0.61)):
            result = categorize_transaction(
                self.session,
                user_id=1,
                description="Rajpal payment",
                amount=150,
                transaction_type="expense",
            )

        self.assertEqual(result["method"], "needs_review")
        self.assertEqual(result["category_name"], "Needs Review")
        self.assertEqual(result["suggested_category_name"], "Food")
        self.assertEqual(result["confidence"], 0.61)
        self.assertEqual(result["review_status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
