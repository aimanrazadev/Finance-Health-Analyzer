import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import Category, Friend, FriendMerchantLearning, FriendTransactionLink, Transaction
from app.services.category_service import seed_default_categories
from app.services.friend_detection_service import detect_friend_for_transaction
from app.services.friend_service import auto_attach_matching_transactions, normalize_friend_name


class FriendTrackingTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()
        seed_default_categories(self.session)

    def tearDown(self):
        self.session.close()

    def add_friend(self, name="Aiman Raza", user_id=1):
        friend = Friend(user_id=user_id, name=name, normalized_name=normalize_friend_name(name))
        self.session.add(friend)
        self.session.commit()
        self.session.refresh(friend)
        return friend

    def add_transaction(self, description, user_id=1):
        transaction = Transaction(
            user_id=user_id,
            amount=250,
            description=description,
            merchant=None,
            transaction_type="expense",
            date=datetime(2026, 5, 1),
            category_confidence=0.30,
            categorization_method="needs_review",
            review_status="needs_review",
            is_needs_review=True,
        )
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def friends_category_id(self):
        return self.session.query(Category).filter(Category.name == "Friends").one().id

    def test_friend_detection_matches_name_in_transaction_description(self):
        friend = self.add_friend("Aiman Raza")
        transaction = self.add_transaction("UPI/AIMAN RAZA/778899/Payment from Ph")

        suggestion = detect_friend_for_transaction(self.session, 1, transaction)

        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion["friend_id"], friend.id)
        self.assertEqual(suggestion["friend_name"], "Aiman Raza")
        self.assertEqual(suggestion["reason"], "friend_name_match")
        self.assertGreaterEqual(suggestion["confidence"], 0.70)

    def test_auto_attach_groups_matching_transactions_and_keeps_history_safe(self):
        friend = self.add_friend("Aiman")
        first = self.add_transaction("UPI/AIMAN/778899/Payment from Ph")
        second = self.add_transaction("Received from Aiman for lunch")
        unrelated = self.add_transaction("Zomato dinner order")

        attached_count = auto_attach_matching_transactions(self.session, 1, friend)
        self.session.commit()

        self.assertEqual(attached_count, 2)
        for transaction_id in (first.id, second.id):
            transaction = self.session.get(Transaction, transaction_id)
            self.assertEqual(transaction.friend_id, friend.id)
            self.assertTrue(transaction.is_friend_transaction)
            self.assertFalse(transaction.is_needs_review)
            self.assertEqual(transaction.review_status, "approved")
            self.assertEqual(transaction.category_id, self.friends_category_id())
            self.assertEqual(transaction.categorization_method, "friend_match")
            self.assertEqual(transaction.category_confidence, 0.95)

        untouched = self.session.get(Transaction, unrelated.id)
        self.assertIsNone(untouched.friend_id)
        self.assertFalse(untouched.is_friend_transaction)
        self.assertEqual(untouched.review_status, "needs_review")

        links = self.session.query(FriendTransactionLink).filter(FriendTransactionLink.friend_id == friend.id).all()
        learned = self.session.query(FriendMerchantLearning).filter(FriendMerchantLearning.friend_id == friend.id).all()
        self.assertEqual(len(links), 2)
        self.assertEqual(len(learned), 2)


if __name__ == "__main__":
    unittest.main()
