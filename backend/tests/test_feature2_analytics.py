import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.models import Category, Transaction, User
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
        ))

    def test_dashboard_uses_statement_balance_and_intentional_savings(self):
        summary = build_dashboard_summary(self.db, self.user.id, 6, 2026)

        self.assertEqual(summary.current_balance, 28000)
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


if __name__ == "__main__":
    unittest.main()
