import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import Category
from app.schemas.schemas import CategoryCreate
from app.services.category_service import (
    VISIBLE_CATEGORY_ORDER,
    create_category,
    get_visible_categories,
    seed_default_categories,
)


class CategoryServiceTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()

    def tearDown(self):
        self.session.close()

    def test_seed_default_categories_creates_required_module_3_categories(self):
        seed_default_categories(self.session)

        names = {category.name for category in self.session.query(Category).all()}
        for name in ["Food", "Transport", "Shopping", "Rent", "Bills", "Entertainment", "Salary", "Other"]:
            self.assertIn(name, names)
        self.assertNotIn("Needs Review", names)

        food = self.session.query(Category).filter(Category.name == "Food").one()
        self.assertEqual(food.color, "#fca5a5")
        self.assertEqual(food.icon, "utensils")

    def test_get_visible_categories_returns_product_order_without_needs_review(self):
        seed_default_categories(self.session)

        names = [category.name for category in get_visible_categories(self.session)]

        self.assertEqual(names, VISIBLE_CATEGORY_ORDER)
        self.assertNotIn("Needs Review", names)

    def test_create_category_validates_blank_and_duplicate_names(self):
        seed_default_categories(self.session)

        custom = create_category(
            self.session,
            CategoryCreate(name="  Pets  ", description="Pet expenses", color="#f472b6", icon="paw-print"),
        )

        self.assertEqual(custom.name, "Pets")
        self.assertEqual(custom.description, "Pet expenses")

        with self.assertRaises(ValueError):
            create_category(self.session, CategoryCreate(name="Pets"))

        with self.assertRaises(ValueError):
            create_category(self.session, CategoryCreate(name="   "))


if __name__ == "__main__":
    unittest.main()
