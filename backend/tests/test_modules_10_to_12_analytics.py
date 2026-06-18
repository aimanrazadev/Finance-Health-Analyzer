import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import Category, Transaction
from app.services.category_service import seed_default_categories
from app.services.dashboard_insights_service import build_dashboard_insights
from app.services.dashboard_summary_service import build_dashboard_summary, build_monthly_trends
from app.services.financial_analytics_service import (
    build_category_analytics,
    build_complete_dashboard_data,
    build_merchant_analytics_detail,
    build_savings_analytics,
    build_subscription_analytics,
)
from app.services.spending_insights import build_spending_summary, fallback_insights


class AnalyticsDashboardTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()
        seed_default_categories(self.session)

    def tearDown(self):
        self.session.close()

    def category_id(self, name):
        return self.session.query(Category).filter(Category.name == name).one().id

    def add_transaction(self, amount, description, category_name, transaction_type="expense", month=6, merchant=None):
        transaction = Transaction(
            user_id=1,
            amount=amount,
            category_id=self.category_id(category_name),
            description=description,
            merchant=merchant,
            extracted_merchant=merchant,
            transaction_type=transaction_type,
            date=datetime(2026, month, 10),
            source="manual",
            category_confidence=1,
            categorization_method="manual",
            review_status="approved",
        )
        self.session.add(transaction)
        return transaction

    def test_dashboard_summary_calculates_savings_top_merchant_and_health(self):
        self.add_transaction(50000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.add_transaction(7000, "Zomato month spend", "Food", month=6, merchant="Zomato")
        self.add_transaction(3000, "Netflix subscription", "Subscriptions", month=6, merchant="Netflix")
        self.add_transaction(5000, "Mutual fund SIP", "Investments", month=6, merchant="Groww")
        self.session.commit()

        summary = build_dashboard_summary(self.session, 1, 6, 2026)

        self.assertEqual(summary.total_income, 50000)
        self.assertEqual(summary.total_expenses, 10000)
        self.assertEqual(summary.investment_amount, 5000)
        self.assertEqual(summary.remaining_money, 35000)
        self.assertEqual(summary.total_savings, 40000)
        self.assertEqual(summary.top_merchant, "Zomato")
        self.assertEqual(summary.recurring_subscription_count, 1)
        self.assertGreater(summary.financial_health_score, 0)
        self.assertIn(summary.financial_health_status, {"Excellent", "Good", "Average", "Needs Improvement"})

    def test_savings_category_and_merchant_analytics_return_module_outputs(self):
        self.add_transaction(50000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.add_transaction(7000, "Zomato month spend", "Food", month=6, merchant="Zomato")
        self.add_transaction(3000, "Uber rides", "Transport", month=6, merchant="Uber")
        self.add_transaction(1000, "Uber airport", "Transport", month=6, merchant="Uber")
        self.add_transaction(45000, "May salary", "Salary", "income", month=5, merchant="Employer")
        self.add_transaction(5000, "May food", "Food", month=5, merchant="Zomato")
        self.session.commit()

        savings = build_savings_analytics(self.session, 1, 6, 2026)
        categories = build_category_analytics(self.session, 1, 6, 2026)
        merchants = build_merchant_analytics_detail(self.session, 1, 6, 2026)

        self.assertEqual(savings.savings, 39000)
        self.assertGreater(savings.savings_rate, 0)
        self.assertEqual(categories.highest_spending_category, "Food")
        self.assertEqual(categories.total_expenses, 11000)
        self.assertEqual(merchants.top_merchants[0].merchant_name, "Zomato")
        self.assertEqual(merchants.most_frequent_merchants[0].merchant_name, "Uber")

    def test_dashboard_insights_generate_readable_signals(self):
        self.add_transaction(50000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.add_transaction(14000, "OpenAI ChatGPT subscription", "Subscriptions", month=6, merchant="Openai")
        self.add_transaction(8000, "Zomato dinner", "Food", month=6, merchant="Zomato")
        self.add_transaction(50000, "May salary", "Salary", "income", month=5, merchant="Employer")
        self.add_transaction(5000, "May subscription", "Subscriptions", month=5, merchant="Openai")
        self.session.commit()

        response = build_dashboard_insights(self.session, 1, 6, 2026)
        insight_text = " ".join(item.message for item in response.insights)

        self.assertGreaterEqual(len(response.insights), 3)
        self.assertLessEqual(len(response.insights), 5)
        self.assertIn("Openai", insight_text)
        self.assertTrue(any(item.severity in {"positive", "warning", "neutral"} for item in response.insights))

    def test_monthly_trends_calculate_income_expenses_savings_and_investments(self):
        self.add_transaction(50000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.add_transaction(12000, "June rent", "Rent", month=6, merchant="Landlord")
        self.add_transaction(8000, "June SIP", "Investments", month=6, merchant="Groww")
        self.add_transaction(45000, "May salary", "Salary", "income", month=5, merchant="Employer")
        self.add_transaction(15000, "May rent", "Rent", month=5, merchant="Landlord")
        self.session.commit()

        trends = build_monthly_trends(self.session, 1, 2026)
        june = next(item for item in trends.trends if item.month == "Jun")

        self.assertEqual(june.income, 50000)
        self.assertEqual(june.expenses, 12000)
        self.assertEqual(june.investments, 8000)
        self.assertEqual(june.savings, 38000)

    def test_spending_summary_detects_top_merchant_and_subscription_category_only(self):
        self.add_transaction(12000, "OpenAI ChatGPT subscription", "Subscriptions", month=6, merchant="Openai")
        self.add_transaction(5000, "Netflix food typo", "Food", month=6, merchant="Netflix")
        self.add_transaction(45000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.session.commit()

        summary = build_spending_summary(self.session, 1, 6, 2026)
        insights = fallback_insights(summary)
        insight_text = " ".join(item["text"] for item in insights)

        self.assertEqual(summary["top_merchant"]["merchant"], "Openai")
        self.assertEqual(len(summary["subscriptions"]), 1)
        self.assertIn("Openai", insight_text)

    def test_subscription_analytics_detects_and_stores_subscription_rows(self):
        self.add_transaction(999, "Spotify monthly", "Subscriptions", month=5, merchant="Spotify")
        self.add_transaction(999, "Spotify monthly", "Subscriptions", month=6, merchant="Spotify")
        self.add_transaction(1999, "Netflix but food category", "Food", month=6, merchant="Netflix")
        self.session.commit()

        response = build_subscription_analytics(self.session, 1, 6, 2026)

        self.assertEqual(response.subscription_count, 1)
        self.assertEqual(response.total_monthly_cost, 999)
        self.assertEqual(response.subscriptions[0].merchant_name, "Spotify")
        self.assertGreaterEqual(response.subscriptions[0].confidence, 0.90)

    def test_complete_dashboard_payload_combines_all_feature_2_modules(self):
        self.add_transaction(50000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.add_transaction(7000, "Zomato month spend", "Food", month=6, merchant="Zomato")
        self.add_transaction(999, "Spotify monthly", "Subscriptions", month=6, merchant="Spotify")
        self.session.commit()

        payload = build_complete_dashboard_data(self.session, 1, 6, 2026)

        self.assertEqual(payload.summary.total_income, 50000)
        self.assertEqual(payload.categories.highest_spending_category, "Food")
        self.assertEqual(payload.merchants.top_merchants[0].merchant_name, "Zomato")
        self.assertEqual(payload.subscriptions.subscription_count, 1)
        self.assertGreaterEqual(len(payload.insights.insights), 3)


if __name__ == "__main__":
    unittest.main()
