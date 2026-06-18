import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import Category, ImportProfile, Merchant, Transaction
from app.services.advisor_actions_service import run_advisor_action
from app.services.category_service import seed_default_categories
from app.services.financial_snapshot_service import build_financial_snapshot
from app.services.import_profile_service import resolve_import_mapping, save_import_profile_from_columns
from app.services.merchant_service import rename_merchant, sync_merchants_from_transactions


class DevelopmentPhase2TestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()
        seed_default_categories(self.session)

    def tearDown(self):
        self.session.close()

    def category_id(self, name):
        return self.session.query(Category).filter(Category.name == name).one().id

    def add_transaction(self, amount, description, category_name, transaction_type="expense", merchant=None, month=6):
        transaction = Transaction(
            user_id=1,
            amount=amount,
            description=description,
            merchant=merchant,
            extracted_merchant=merchant,
            transaction_type=transaction_type,
            category_id=self.category_id(category_name),
            date=datetime(2026, month, 10),
            category_confidence=1,
            categorization_method="manual",
            review_status="approved",
        )
        self.session.add(transaction)
        return transaction

    def test_import_profile_saves_and_reuses_column_mapping(self):
        columns = ["Txn Date", "Narration", "Debit", "Credit", "Balance"]
        profile = save_import_profile_from_columns(
            self.session,
            user_id=1,
            file_name="HDFC Statement.csv",
            file_type="csv",
            columns=columns,
        )
        self.session.commit()

        reused = resolve_import_mapping(self.session, 1, "HDFC Statement.csv", "csv", columns)

        self.assertIsInstance(profile, ImportProfile)
        self.assertEqual(reused["profile"].id, profile.id)
        self.assertEqual(reused["mapping"]["Txn Date"], "transaction_date")
        self.assertGreaterEqual(reused["confidence"], 0.6)

    def test_merchant_directory_sync_and_global_rename(self):
        self.add_transaction(1200, "AMZN MKTP order", "Shopping", merchant="AMZN MKTP")
        self.add_transaction(900, "Amazon India order", "Shopping", merchant="Amazon India")
        self.session.commit()

        merchants = sync_merchants_from_transactions(self.session, 1)
        merchant = self.session.query(Merchant).filter(Merchant.user_id == 1).first()
        renamed = rename_merchant(self.session, 1, merchant.id, "Amazon")
        names = {transaction.merchant for transaction in self.session.query(Transaction).all()}

        self.assertGreaterEqual(len(merchants), 1)
        self.assertEqual(renamed.canonical_name, "Amazon")
        self.assertEqual(names, {"Amazon"})

    def test_financial_snapshot_projects_month_end_values(self):
        self.add_transaction(60000, "June salary", "Salary", "income", merchant="Employer")
        self.add_transaction(12000, "Zomato food", "Food", merchant="Zomato")
        self.session.commit()

        snapshot = build_financial_snapshot(self.session, 1, 6, 2026)

        self.assertEqual(snapshot.current_month_spending, 12000)
        self.assertEqual(snapshot.top_category, "Food")
        self.assertEqual(snapshot.top_merchant, "Zomato")
        self.assertGreaterEqual(len(snapshot.alerts), 1)

    def test_advisor_action_search_and_report_use_safe_filters(self):
        self.add_transaction(650, "Zomato dinner", "Food", merchant="Zomato")
        self.add_transaction(300, "Zomato snack", "Food", merchant="Zomato")
        self.add_transaction(50000, "June salary", "Salary", "income", merchant="Employer")
        self.session.commit()

        search = run_advisor_action(self.session, 1, "Show all Zomato transactions above 500 from June 2026")
        report = run_advisor_action(self.session, 1, "Generate monthly report for June 2026")

        self.assertEqual(search.action_type, "search")
        self.assertEqual(len(search.transactions), 1)
        self.assertEqual(search.filters["merchant"], "Zomato")
        self.assertEqual(report.action_type, "report")
        self.assertEqual(report.report["income"], 50000)


if __name__ == "__main__":
    unittest.main()
