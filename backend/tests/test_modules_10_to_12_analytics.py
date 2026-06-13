import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import AccountBalance, Budget, Category, SuggestedBudget, Transaction
from app.services.category_service import seed_default_categories
from app.services.dashboard_summary_service import (
    build_budget_usage_chart,
    build_dashboard_summary,
    generate_suggested_budgets,
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
            review_status="approved",
        )
        self.session.add(transaction)
        return transaction

    def test_dashboard_summary_calculates_effective_savings_top_merchant_and_budget_health(self):
        self.add_transaction(50000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.add_transaction(7000, "Zomato month spend", "Food", month=6, merchant="Zomato")
        self.add_transaction(3000, "Netflix subscription", "Subscriptions", month=6, merchant="Netflix")
        self.add_transaction(5000, "Mutual fund SIP", "Investments", month=6, merchant="Groww")
        self.add_transaction(45000, "May salary", "Salary", "income", month=5, merchant="Employer")
        self.add_transaction(10000, "May food", "Food", month=5, merchant="Zomato")
        self.session.add(AccountBalance(user_id=1, account_name="Kotak 811", balance_amount=12000))
        self.session.add(Budget(user_id=1, category_id=self.category_id("Food"), amount=6000, period="2026-06", alert_threshold=0))
        self.session.commit()

        summary = build_dashboard_summary(self.session, 1, 6, 2026)
        budget_usage = build_budget_usage_chart(self.session, 1, 6, 2026)

        self.assertEqual(summary.total_income, 50000)
        self.assertEqual(summary.total_expenses, 15000)
        self.assertEqual(summary.total_savings, 35000)
        self.assertEqual(summary.investment_savings, 5000)
        self.assertEqual(summary.remaining_balance_savings, 12000)
        self.assertEqual(summary.effective_savings, 52000)
        self.assertEqual(summary.top_merchant, "Zomato")
        self.assertEqual(summary.recurring_subscription_count, 1)
        self.assertEqual(budget_usage[0].status, "over_budget")
        self.assertGreater(summary.budget_health_score, 0)

    def test_auto_budget_engine_generates_and_stores_suggestions_from_category_averages(self):
        for month, amount in [(3, 3000), (4, 6000), (5, 9000)]:
            self.add_transaction(amount, f"Food spend {month}", "Food", month=month, merchant="Swiggy")
        self.session.commit()

        suggestions = generate_suggested_budgets(self.session, 1, 6, 2026, store=True)
        food_suggestion = next(item for item in suggestions if item.category_name == "Food")
        stored = self.session.query(SuggestedBudget).filter(SuggestedBudget.category_id == self.category_id("Food")).one()

        self.assertEqual(food_suggestion.average_spend, 6000)
        self.assertEqual(food_suggestion.suggested_amount, 6600)
        self.assertEqual(stored.suggested_amount, 6600)

    def test_smart_insights_summary_detects_merchant_savings_and_budget_variance(self):
        self.add_transaction(40000, "June salary", "Salary", "income", month=6, merchant="Employer")
        self.add_transaction(12000, "OpenAI ChatGPT subscription", "Subscriptions", month=6, merchant="Openai")
        self.add_transaction(45000, "May salary", "Salary", "income", month=5, merchant="Employer")
        self.add_transaction(5000, "May subscription", "Subscriptions", month=5, merchant="Openai")
        self.session.add(Budget(user_id=1, category_id=self.category_id("Subscriptions"), amount=6000, period="2026-06", alert_threshold=0))
        self.session.commit()

        summary = build_spending_summary(self.session, 1, 6, 2026)
        insights = fallback_insights(summary)
        insight_text = " ".join(item["text"] for item in insights)

        self.assertEqual(summary["top_merchant"]["merchant"], "Openai")
        self.assertEqual(summary["budget_variances"][0]["category"], "Subscriptions")
        self.assertIn("Openai", insight_text)
        self.assertIn("over budget", insight_text)


if __name__ == "__main__":
    unittest.main()
