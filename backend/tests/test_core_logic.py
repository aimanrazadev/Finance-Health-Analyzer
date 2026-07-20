import unittest
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analytics.financial_analytics import _month_start_months_ago, build_subscription_analytics
from app.ml.categorization import MIN_TRAINING_LABELS, _learning_accuracy_cached, _manual_correction_rows, train_user_category_model
from app.models.models import (
    Category,
    CategoryCorrection,
    Friend,
    FriendMerchantLearning,
    FriendTransactionLink,
    Subscription,
    Transaction,
)
from app.services.categorization_service import _keyword_prediction
from app.services.friend_service import merge_friend_into_existing
from app.ai.structured_insights import validate_llm_content
from app.schemas.schemas import AIFinancialContext


class CategorizationLogicTests(unittest.TestCase):
    def test_grocery_keywords_are_not_claimed_by_food(self):
        category, confidence = _keyword_prediction(
            "Blinkit supermarket grocery order",
            transaction_type="expense",
        )
        self.assertEqual(category, "Groceries")
        self.assertGreaterEqual(confidence, 0.8)

    def test_expense_credit_text_is_not_salary(self):
        category, _confidence = _keyword_prediction(
            "credit card payment",
            transaction_type="expense",
        )
        self.assertNotEqual(category, "Salary")


class LearningAccuracyTests(unittest.TestCase):
    def setUp(self):
        _learning_accuracy_cached.cache_clear()

    def test_too_few_corrections_returns_honest_status(self):
        rows = tuple((f"transaction {index}", "Food") for index in range(MIN_TRAINING_LABELS - 1))
        result = _learning_accuracy_cached(rows, 0.2)
        self.assertEqual(result["status"], "not_enough_data")
        self.assertIsNone(result["accuracy_percent"])
        self.assertEqual(result["correction_count"], MIN_TRAINING_LABELS - 1)

    def test_ready_result_reports_consistent_counts(self):
        rows = tuple(
            (f"{'restaurant' if index % 2 else 'store'} transaction {index}", "Food" if index % 2 else "Shopping")
            for index in range(30)
        )
        result = _learning_accuracy_cached(rows, 0.2)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["training_count"] + result["test_count"], result["correction_count"])
        self.assertLessEqual(result["correct_count"], result["test_count"])

    def test_latest_correction_per_transaction_keeps_repeated_descriptions(self):
        engine = create_engine("sqlite:///:memory:")
        Category.__table__.create(engine)
        CategoryCorrection.__table__.create(engine)
        Transaction.__table__.create(engine)
        session = sessionmaker(bind=engine)()
        food = Category(name="Food")
        shopping = Category(name="Shopping")
        session.add_all([food, shopping])
        session.flush()
        session.add_all([
            CategoryCorrection(user_id=1, transaction_id=1, new_category_id=food.id,
                               original_description="Same merchant", created_at=datetime(2026, 1, 1)),
            CategoryCorrection(user_id=1, transaction_id=1, new_category_id=shopping.id,
                               original_description="Same merchant", created_at=datetime(2026, 1, 2)),
            CategoryCorrection(user_id=1, transaction_id=2, new_category_id=food.id,
                               original_description="Same merchant", created_at=datetime(2026, 1, 3)),
        ])
        session.commit()
        rows = _manual_correction_rows(session, 1)
        session.close()
        self.assertEqual(len(rows), 2)
        self.assertIn(("Same merchant", "Shopping"), rows)
        self.assertIn(("Same merchant", "Food"), rows)


class FriendMergeTests(unittest.TestCase):
    def test_merge_moves_transactions_and_learning_to_target(self):
        engine = create_engine("sqlite:///:memory:")
        for table in (Friend.__table__, FriendTransactionLink.__table__, FriendMerchantLearning.__table__, Transaction.__table__):
            table.create(engine)
        session = sessionmaker(bind=engine)()
        source = Friend(user_id=1, name="Old Name", normalized_name="old name")
        target = Friend(user_id=1, name="Correct Name", normalized_name="correct name")
        session.add_all([source, target])
        session.flush()
        transaction = Transaction(
            user_id=1,
            friend_id=source.id,
            amount=250,
            description="UPI old name",
            transaction_type="expense",
            date=datetime(2026, 1, 1),
            is_friend_transaction=True,
            normalized_friend_name=source.normalized_name,
        )
        session.add(transaction)
        session.flush()
        session.add_all([
            FriendTransactionLink(user_id=1, friend_id=source.id, transaction_id=transaction.id),
            FriendMerchantLearning(
                user_id=1,
                friend_id=source.id,
                merchant_name="Old Name",
                normalized_merchant="old name",
            ),
        ])
        session.commit()

        merged, moved_count = merge_friend_into_existing(session, 1, source.id, target.id)
        session.commit()

        self.assertEqual(moved_count, 1)
        self.assertEqual(merged.id, target.id)
        self.assertEqual(transaction.friend_id, target.id)
        self.assertEqual(transaction.normalized_friend_name, target.normalized_name)
        self.assertEqual(merged.transaction_count, 1)
        self.assertIsNone(session.query(Friend).filter(Friend.id == source.id).first())
        self.assertEqual(session.query(FriendTransactionLink).one().friend_id, target.id)
        self.assertEqual(session.query(FriendMerchantLearning).one().friend_id, target.id)
        session.close()


class LearningModelTrainingTests(unittest.TestCase):
    def test_single_category_does_not_train_logistic_regression(self):
        engine = create_engine("sqlite:///:memory:")
        Category.__table__.create(engine)
        CategoryCorrection.__table__.create(engine)
        Transaction.__table__.create(engine)
        session = sessionmaker(bind=engine)()
        food = Category(name="Food")
        session.add(food)
        session.flush()
        session.add_all([
            CategoryCorrection(user_id=9, transaction_id=index, new_category_id=food.id,
                               original_description=f"restaurant {index}")
            for index in range(MIN_TRAINING_LABELS)
        ])
        session.commit()
        self.assertIsNone(train_user_category_model(session, 9))
        session.close()


class SubscriptionPeriodTests(unittest.TestCase):
    def test_six_month_window_crosses_year_boundary(self):
        self.assertEqual(
            _month_start_months_ago(datetime(2026, 2, 28), 5),
            datetime(2025, 9, 1),
        )

    def test_monthly_cost_averages_monthly_totals_not_individual_charges(self):
        engine = create_engine("sqlite:///:memory:")
        Category.__table__.create(engine)
        Transaction.__table__.create(engine)
        Subscription.__table__.create(engine)
        session = sessionmaker(bind=engine)()
        category = Category(name="Subscriptions")
        session.add(category)
        session.flush()
        session.add_all([
            Transaction(user_id=1, amount=100, category_id=category.id, description="Service",
                        extracted_merchant="Service", transaction_type="expense", date=datetime(2026, 1, 5)),
            Transaction(user_id=1, amount=200, category_id=category.id, description="Service",
                        extracted_merchant="Service", transaction_type="expense", date=datetime(2026, 1, 20)),
            Transaction(user_id=1, amount=100, category_id=category.id, description="Service",
                        extracted_merchant="Service", transaction_type="expense", date=datetime(2026, 2, 5)),
        ])
        session.commit()
        result = build_subscription_analytics(session, 1, 2, 2026)
        session.close()
        self.assertEqual(result.subscription_count, 1)
        self.assertEqual(result.subscriptions[0].monthly_cost, 200.0)


class AIValidationTests(unittest.TestCase):
    def test_hallucinated_number_is_rejected(self):
        context = AIFinancialContext.model_validate({
            "period_label": "May 2026", "month": 5, "year": 2026, "transaction_count": 10,
            "core_metrics": {
                "opening_balance": 1000, "total_income": 500, "total_expenses": 300,
                "total_savings": 50, "lifestyle_expenses": 250, "available_funds": 1500,
                "savings_rate": 3.33, "actual_closing_balance": 1200,
                "expected_closing_balance": 1200, "balance_difference": 0,
                "balance_mismatch": False,
            },
            "health_score": {
                "overall_score": 70, "status": "Good",
                "components": {"savings_score": 60, "subscription_score": 80,
                               "spending_stability_score": 70, "financial_balance_score": 70},
            },
            "top_categories": [], "top_merchants": [],
            "subscriptions": {"count": 0, "monthly_total": 0},
            "trends": {},
        })
        raw = json.dumps({
            "summary": "Income was INR 999.", "spending_insights": [],
            "savings_insights": [], "merchant_insights": [],
            "subscription_insights": [], "health_insights": [],
        })
        self.assertIsNone(validate_llm_content(raw, context))


if __name__ == "__main__":
    unittest.main()
