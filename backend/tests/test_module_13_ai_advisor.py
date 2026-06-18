import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import AdvisorMessage, AdvisorRecommendation, Category, Transaction
from app.services.advisor_service import (
    ask_financial_advisor,
    build_advisor_prompt,
    build_financial_context,
    detect_advisor_intent,
    fallback_advisor_response,
    parse_advisor_response,
)
from app.services.category_service import seed_default_categories


class AiAdvisorTestCase(unittest.TestCase):
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

    def seed_financial_month(self):
        self.add_transaction(60000, "June salary", "Salary", "income", merchant="Employer")
        self.add_transaction(12000, "Zomato food orders", "Food", merchant="Zomato")
        self.add_transaction(9000, "Amazon shopping", "Shopping", merchant="Amazon")
        self.add_transaction(1999, "Netflix monthly", "Subscriptions", merchant="Netflix")
        self.add_transaction(12000, "May food orders", "Food", month=5, merchant="Zomato")
        self.add_transaction(1999, "Netflix monthly", "Subscriptions", month=5, merchant="Netflix")
        self.session.commit()

    def test_intent_detection_routes_common_finance_questions(self):
        self.assertEqual(detect_advisor_intent("How can I save more money?"), "savings_advice")
        self.assertEqual(detect_advisor_intent("Where am I overspending?"), "overspending_analysis")
        self.assertEqual(detect_advisor_intent("Explain my health score"), "health_score")
        self.assertEqual(detect_advisor_intent("Which subscriptions should I review?"), "subscription_analysis")

    def test_financial_context_retrieval_uses_feature_2_metrics(self):
        self.seed_financial_month()

        intent, context = build_financial_context(
            self.session,
            user_id=1,
            question="Where am I overspending?",
            month=6,
            year=2026,
        )

        self.assertEqual(intent, "overspending_analysis")
        self.assertEqual(context["monthly_income"], 60000)
        self.assertEqual(context["monthly_expenses"], 22999)
        self.assertEqual(context["transaction_count"], 4)
        self.assertEqual(context["top_categories"][0]["category"], "Food")
        self.assertEqual(context["top_merchants"][0]["merchant"], "Zomato")
        self.assertNotIn("subscriptions", context)

    def test_prompt_contains_guardrails_and_compact_financial_context(self):
        _, context = build_financial_context(
            self.session,
            user_id=1,
            question="How can I save money?",
            month=6,
            year=2026,
        )

        prompt = build_advisor_prompt("How can I save money?", context)

        self.assertIn("Use only the provided financial data", prompt)
        self.assertIn("Do not invent numbers", prompt)
        self.assertIn("Return only valid JSON", prompt)
        self.assertIn("monthly_income", prompt)

    def test_malformed_llm_json_becomes_safe_fallback(self):
        self.seed_financial_month()
        _, context = build_financial_context(
            self.session,
            user_id=1,
            question="How can I save money?",
            month=6,
            year=2026,
        )

        response = parse_advisor_response("not valid json", "How can I save money?", context)

        self.assertIn("Income is INR", response.summary)
        self.assertGreaterEqual(len(response.recommendations), 1)
        self.assertIn("budgeting guidance", response.risk_note)

    def test_missing_financial_data_returns_empty_state_advice(self):
        response = fallback_advisor_response(
            "How can I save money?",
            {"transaction_count": 0},
        )

        self.assertIn("transaction data", response.summary)
        self.assertEqual(response.recommendations, [])

    def test_ask_advisor_saves_chat_messages_and_recommendations(self):
        self.seed_financial_month()
        llm_payload = json.dumps({
            "summary": "Food and shopping are the main pressure areas.",
            "main_problem": "Food spending is high for this month.",
            "recommendations": [
                {
                    "title": "Reduce food delivery",
                    "reason": "Food is your top category.",
                    "impact": "Could save around INR 1,800/month.",
                    "estimated_savings": 1800,
                    "category": "Food",
                }
            ],
            "savings_impact": "Savings can improve if food delivery is reduced.",
            "subscriptions": ["Review Netflix usage"],
            "risk_note": "This is budgeting guidance, not investment, tax, or legal advice.",
        })

        with patch("app.services.advisor_service.LLMClient.generate_text", return_value=llm_payload):
            result = ask_financial_advisor(
                self.session,
                user_id=1,
                question="How can I save more money?",
                month=6,
                year=2026,
            )

        messages = self.session.query(AdvisorMessage).filter(AdvisorMessage.chat_id == result["chat"].id).all()
        recommendations = self.session.query(AdvisorRecommendation).filter(AdvisorRecommendation.user_id == 1).all()

        self.assertEqual(result["intent"], "savings_advice")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].title, "Reduce food delivery")
        self.assertEqual(recommendations[0].status, "pending")

    def test_unrelated_questions_do_not_call_llm(self):
        with patch("app.services.advisor_service.LLMClient.generate_text") as generate_text:
            result = ask_financial_advisor(
                self.session,
                user_id=1,
                question="Tell me a movie plot",
                month=6,
                year=2026,
            )

        generate_text.assert_not_called()
        self.assertIn("budgeting", result["response"].summary)


if __name__ == "__main__":
    unittest.main()
