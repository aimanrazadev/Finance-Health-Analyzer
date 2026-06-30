import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.models import Category, Transaction, UploadedFile, User
from app.services.analytics_service import build_dashboard_summary, build_monthly_trends
from app.services.financial_analytics_service import (
    build_category_analytics,
    build_category_merchant_breakdown,
    build_complete_dashboard_data,
    build_merchant_analytics_detail,
)
from app.services.financial_health_service import calculate_financial_health_score


class Feature2AnalyticsTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.user = User(name="Analytics User", email="analytics@example.com", password_hash="test")
        self.other_user = User(name="Other User", email="other@example.com", password_hash="test")
        self.db.add_all([self.user, self.other_user])
        self.db.flush()

        self.categories = {
            name: Category(name=name, color=color)
            for name, color in {
                "Food": "#ff5252",
                "Shopping": "#ffa43b",
                "Savings": "#a3ff12",
                "Investments": "#23c483",
                "Subscriptions": "#38bdf8",
            }.items()
        }
        self.db.add_all(self.categories.values())
        self.db.flush()

        self._transaction("Salary", 60000, "income", None, 52000, "Employer", 1)
        self._transaction("Zomato", 8000, "expense", "Food", 44000, "Zomato", 5)
        self._transaction("Amazon", 5000, "expense", "Shopping", 39000, "Amazon", 8)
        self._transaction("SIP Investment", 7000, "expense", "Investments", 32000, "Fund House", 12)
        self._transaction("Transfer to Savings", 3000, "expense", "Savings", 29000, "Savings Account", 14)
        self._transaction("Streaming plan", 1000, "expense", "Subscriptions", 28000, "Stream Co", 16)
        self._transaction("Other user expense", 99999, "expense", "Food", 1, "Hidden", 20, self.other_user.id)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _transaction(
        self,
        description,
        amount,
        transaction_type,
        category_name,
        balance,
        merchant,
        day,
        user_id=None,
        month=6,
        year=2026,
        uploaded_file_id=None,
    ):
        self.db.add(Transaction(
            user_id=user_id or self.user.id,
            amount=amount,
            category_id=self.categories[category_name].id if category_name else None,
            description=description,
            merchant=merchant,
            transaction_type=transaction_type,
            date=datetime(year, month, day),
            balance=balance,
            uploaded_file_id=uploaded_file_id,
        ))

    def test_dashboard_uses_statement_balance_and_intentional_savings(self):
        summary = build_dashboard_summary(self.db, self.user.id, 6, 2026)

        self.assertEqual(summary.current_balance, 28000)
        self.assertEqual(summary.closing_balance, 28000)
        self.assertEqual(summary.total_income, 60000)
        self.assertEqual(summary.total_expenses, 24000)
        self.assertEqual(summary.total_savings, 10000)
        self.assertEqual(summary.savings_rate, 16.67)
        self.assertEqual(summary.transaction_count, 6)

    def test_category_and_merchant_spending_excludes_savings_allocations(self):
        categories = build_category_analytics(self.db, self.user.id, 6, 2026)
        details = build_category_merchant_breakdown(self.db, self.user.id, 6, 2026)
        merchants = build_merchant_analytics_detail(self.db, self.user.id, 6, 2026)

        category_names = {item.category_name for item in categories.categories}
        self.assertNotIn("Savings", category_names)
        self.assertNotIn("Investments", category_names)
        self.assertEqual(categories.total_expenses, 14000)
        self.assertAlmostEqual(sum(item.percentage for item in categories.categories), 100, places=1)
        self.assertEqual(details.total_expenses, 14000)
        self.assertNotIn("Fund House", {item.merchant_name for item in merchants.top_merchants})

    def test_monthly_trends_use_category_savings_and_health_has_four_components(self):
        june = build_monthly_trends(self.db, self.user.id, 2026).trends[5]
        health = calculate_financial_health_score(self.db, self.user.id, 6, 2026)

        self.assertEqual(june.savings, 10000)
        self.assertEqual(june.savings_rate, 16.67)
        self.assertEqual(
            [item["label"] for item in health["breakdown"]],
            ["Savings rate", "Subscription control", "Spending stability", "Financial balance"],
        )

    def test_complete_dashboard_payload_contains_health_and_recent_activity(self):
        dashboard = build_complete_dashboard_data(self.db, self.user.id, 6, 2026)

        self.assertEqual(dashboard.summary.current_balance, 28000)
        self.assertEqual(dashboard.summary.closing_balance, 28000)
        self.assertEqual(len(dashboard.recent_transactions), 6)
        self.assertEqual(dashboard.subscriptions.total_annual_cost, 12000)
        self.assertEqual(len(dashboard.health.breakdown), 4)

    def test_month_view_compares_with_previous_calendar_month(self):
        self._transaction("May spending", 12000, "expense", "Food", 40000, "May Merchant", 10, month=5)
        self.db.commit()

        dashboard = build_complete_dashboard_data(self.db, self.user.id, 6, 2026)

        self.assertEqual(dashboard.trends.expense_change_percentage, 100.0)

    def test_january_view_rolls_comparison_back_to_previous_december(self):
        self._transaction("January spending", 15000, "expense", "Food", 30000, "January Merchant", 10, month=1, year=2026)
        self._transaction("December spending", 10000, "expense", "Food", 45000, "December Merchant", 10, month=12, year=2025)
        self.db.commit()

        dashboard = build_complete_dashboard_data(self.db, self.user.id, 1, 2026)

        self.assertEqual(dashboard.trends.expense_change_percentage, 50.0)

    def test_year_view_compares_with_previous_full_year(self):
        self._transaction("Prior year income", 30000, "income", None, 30000, "Prior Employer", 10, year=2025)
        self._transaction("Prior year spending", 12000, "expense", "Food", 18000, "Prior Merchant", 11, year=2025)
        self.db.commit()

        dashboard = build_complete_dashboard_data(self.db, self.user.id, 0, 2026)

        self.assertEqual(dashboard.trends.income_change_percentage, 100.0)
        self.assertEqual(dashboard.trends.expense_change_percentage, 100.0)

    def test_opening_balance_uses_previous_month_closing_balance_without_changing_income(self):
        user = User(name="Opening Balance User", email="opening@example.com", password_hash="test")
        self.db.add(user)
        self.db.flush()
        self._transaction("June closing activity", 1000, "expense", "Food", 25000, "June Merchant", 28, user.id)
        self._transaction("July spending", 5000, "expense", "Food", 20000, "July Merchant", 3, user.id, month=7)
        self.db.commit()

        summary = build_dashboard_summary(self.db, user.id, 7, 2026)
        july_trend = build_monthly_trends(self.db, user.id, 2026).trends[6]

        self.assertEqual(summary.total_income, 0)
        self.assertEqual(summary.opening_balance, 25000)
        self.assertEqual(summary.total_expenses, 5000)
        self.assertEqual(july_trend.income, 0)

    def test_opening_balance_is_derived_from_first_statement_row(self):
        user = User(name="Derived Opening User", email="derived-opening@example.com", password_hash="test")
        self.db.add(user)
        self.db.flush()
        self._transaction("First monthly purchase", 4000, "expense", "Food", 16000, "First Merchant", 2, user.id, month=8)
        self.db.commit()

        summary = build_dashboard_summary(self.db, user.id, 8, 2026)

        self.assertEqual(summary.total_income, 0)
        self.assertEqual(summary.opening_balance, 20000)
        self.assertEqual(summary.total_expenses, 4000)

    def test_real_monthly_income_and_opening_balance_are_reported_separately(self):
        user = User(name="Income Priority User", email="income-priority@example.com", password_hash="test")
        self.db.add(user)
        self.db.flush()
        self._transaction("Prior closing activity", 1000, "expense", "Food", 50000, "Prior Merchant", 28, user.id)
        self._transaction("Monthly salary", 30000, "income", None, 80000, "Employer", 1, user.id, month=7)
        self.db.commit()

        summary = build_dashboard_summary(self.db, user.id, 7, 2026)

        self.assertEqual(summary.total_income, 30000)
        self.assertEqual(summary.opening_balance, 50000)

    def test_real_statement_math_uses_stored_pdf_opening_balance(self):
        user = User(name="Statement Math User", email="statement-math@example.com", password_hash="test")
        self.db.add(user)
        self.db.flush()
        uploaded_file = UploadedFile(
            user_id=user.id,
            filename="statement.pdf",
            file_path="confirmed-import://statement.pdf",
            file_type="pdf",
            file_size=1000,
            opening_balance=5359.96,
            closing_balance=1760.96,
        )
        self.db.add(uploaded_file)
        self.db.flush()
        self._transaction(
            "Monthly expenses",
            3599.00,
            "expense",
            "Food",
            1760.96,
            "Merchant",
            28,
            user.id,
            uploaded_file_id=uploaded_file.id,
        )
        self.db.commit()

        summary = build_dashboard_summary(self.db, user.id, 6, 2026)
        health = calculate_financial_health_score(self.db, user.id, 6, 2026)

        self.assertEqual(summary.opening_balance, 5359.96)
        self.assertEqual(summary.total_income, 0)
        self.assertEqual(summary.total_expenses, 3599.00)
        self.assertEqual(summary.lifestyle_expenses, 3599.00)
        self.assertEqual(summary.available_funds, 5359.96)
        self.assertEqual(summary.current_balance, 1760.96)
        self.assertEqual(summary.closing_balance, 1760.96)
        self.assertEqual(summary.pdf_closing_balance, 1760.96)
        self.assertEqual(summary.expected_closing_balance, 1760.96)
        self.assertFalse(summary.balance_mismatch)
        self.assertEqual(summary.calculated_closing_balance, 1760.96)
        self.assertEqual(summary.balance_difference, 0)
        self.assertEqual(summary.savings_rate, 0)
        self.assertEqual(health["balance_score"], 70)

    def test_savings_rate_uses_available_funds_across_all_sources(self):
        scenarios = [
            {
                "name": "Opening Funds Only",
                "email": "opening-funds-only@example.com",
                "opening": 100000,
                "income": 0,
                "savings": 20000,
                "lifestyle": 20000,
            },
            {
                "name": "Opening And Income",
                "email": "opening-and-income@example.com",
                "opening": 10000,
                "income": 40000,
                "savings": 10000,
                "lifestyle": 0,
            },
            {
                "name": "Income Only",
                "email": "income-only@example.com",
                "opening": 0,
                "income": 60000,
                "savings": 12000,
                "lifestyle": 0,
            },
        ]

        for index, scenario in enumerate(scenarios, start=1):
            user = User(name=scenario["name"], email=scenario["email"], password_hash="test")
            self.db.add(user)
            self.db.flush()
            uploaded_file = UploadedFile(
                user_id=user.id,
                filename=f"scenario-{index}.pdf",
                file_path=f"confirmed-import://scenario-{index}.pdf",
                file_type="pdf",
                file_size=1000,
                opening_balance=scenario["opening"],
            )
            self.db.add(uploaded_file)
            self.db.flush()

            running_balance = scenario["opening"]
            day = 1
            if scenario["income"]:
                running_balance += scenario["income"]
                self._transaction(
                    "Income",
                    scenario["income"],
                    "income",
                    None,
                    running_balance,
                    "Employer",
                    day,
                    user.id,
                    uploaded_file_id=uploaded_file.id,
                )
                day += 1

            running_balance -= scenario["savings"]
            self._transaction(
                "Intentional savings",
                scenario["savings"],
                "expense",
                "Investments",
                running_balance,
                "Fund House",
                day,
                user.id,
                uploaded_file_id=uploaded_file.id,
            )
            if scenario["lifestyle"]:
                running_balance -= scenario["lifestyle"]
                self._transaction(
                    "Lifestyle spending",
                    scenario["lifestyle"],
                    "expense",
                    "Food",
                    running_balance,
                    "Merchant",
                    day + 1,
                    user.id,
                    uploaded_file_id=uploaded_file.id,
                )

            self.db.commit()
            summary = build_dashboard_summary(self.db, user.id, 6, 2026)

            self.assertEqual(summary.available_funds, scenario["opening"] + scenario["income"])
            self.assertEqual(summary.total_savings, scenario["savings"])
            self.assertEqual(summary.savings_rate, 20)

    def test_current_balance_is_latest_real_balance_while_closing_is_period_specific(self):
        user = User(name="Balance Semantics User", email="balance-semantics@example.com", password_hash="test")
        self.db.add(user)
        self.db.flush()
        self._transaction("May closing", 1000, "expense", "Food", 40000, "May Merchant", 20, user.id, month=5)
        self._transaction("June closing", 10000, "expense", "Food", 30000, "June Merchant", 20, user.id, month=6)
        self.db.commit()

        may = build_dashboard_summary(self.db, user.id, 5, 2026)

        self.assertEqual(may.current_balance, 30000)
        self.assertEqual(may.closing_balance, 40000)

    def test_pdf_closing_balance_wins_and_is_scoped_to_selected_month(self):
        user = User(name="PDF Balance User", email="pdf-balance@example.com", password_hash="test")
        self.db.add(user)
        self.db.flush()

        may_statement = UploadedFile(
            user_id=user.id,
            filename="may.pdf",
            file_path="confirmed-import://may.pdf",
            file_type="pdf",
            file_size=1000,
            opening_balance=7023,
            closing_balance=5360,
        )
        june_statement = UploadedFile(
            user_id=user.id,
            filename="june.pdf",
            file_path="confirmed-import://june.pdf",
            file_type="pdf",
            file_size=1000,
            opening_balance=5360,
            closing_balance=9000,
        )
        self.db.add_all([may_statement, june_statement])
        self.db.flush()

        self._transaction("May income", 29051, "income", None, 36074, "Employer", 2, user.id, month=5, uploaded_file_id=may_statement.id)
        self._transaction("May expenses", 25865, "expense", "Food", 10209, "Merchant", 30, user.id, month=5, uploaded_file_id=may_statement.id)
        self._transaction("June activity", 1000, "expense", "Food", 9000, "Merchant", 30, user.id, month=6, uploaded_file_id=june_statement.id)
        self.db.commit()

        may = build_dashboard_summary(self.db, user.id, 5, 2026)

        self.assertEqual(may.opening_balance, 7023)
        self.assertEqual(may.expected_closing_balance, 10209)
        self.assertEqual(may.pdf_closing_balance, 5360)
        self.assertEqual(may.closing_balance, 5360)
        self.assertEqual(may.balance_difference, -4849)
        self.assertTrue(may.balance_mismatch)

    def test_multimonth_pdf_summary_balances_only_apply_at_statement_boundaries(self):
        user = User(name="Multi Month User", email="multi-month@example.com", password_hash="test")
        self.db.add(user)
        self.db.flush()
        statement = UploadedFile(
            user_id=user.id,
            filename="march-to-may.pdf",
            file_path="confirmed-import://march-to-may.pdf",
            file_type="pdf",
            file_size=1000,
            opening_balance=1000,
            closing_balance=700,
        )
        self.db.add(statement)
        self.db.flush()
        self._transaction("March expense", 100, "expense", "Food", 900, "Merchant", 31, user.id, month=3, uploaded_file_id=statement.id)
        self._transaction("April expense", 100, "expense", "Food", 800, "Merchant", 30, user.id, month=4, uploaded_file_id=statement.id)
        self._transaction("May expense", 100, "expense", "Food", 700, "Merchant", 31, user.id, month=5, uploaded_file_id=statement.id)
        self.db.commit()

        february = build_dashboard_summary(self.db, user.id, 2, 2026)
        march = build_dashboard_summary(self.db, user.id, 3, 2026)
        april = build_dashboard_summary(self.db, user.id, 4, 2026)
        may = build_dashboard_summary(self.db, user.id, 5, 2026)

        self.assertEqual(february.closing_balance, 1000)
        self.assertEqual(march.opening_balance, 1000)
        self.assertIsNone(march.pdf_closing_balance)
        self.assertEqual(april.opening_balance, 900)
        self.assertIsNone(april.pdf_closing_balance)
        self.assertEqual(april.closing_balance, 800)
        self.assertEqual(may.opening_balance, 800)
        self.assertEqual(may.pdf_closing_balance, 700)
        self.assertEqual(may.closing_balance, 700)


if __name__ == "__main__":
    unittest.main()
