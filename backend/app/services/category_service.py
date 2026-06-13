from sqlalchemy.orm import Session

from app.models.models import Category
from app.schemas.schemas import CategoryCreate


DEFAULT_CATEGORY_DEFINITIONS = [
    {"name": "Debt Cleared", "description": "Settled debts and repayments", "color": "#5eead4", "icon": "check-circle"},
    {"name": "Refunds", "description": "Refunds and reversed charges", "color": "#86efac", "icon": "rotate-ccw"},
    {"name": "Bills", "description": "Utilities, recharge, and recurring bills", "color": "#fcd34d", "icon": "receipt"},
    {"name": "Subscriptions", "description": "Streaming, software, and recurring subscriptions", "color": "#c4b5fd", "icon": "repeat"},
    {"name": "Education", "description": "Courses, books, and learning expenses", "color": "#93c5fd", "icon": "graduation-cap"},
    {"name": "Entertainment", "description": "Movies, events, games, and leisure", "color": "#f9a8d4", "icon": "ticket"},
    {"name": "Food", "description": "Restaurants, cafes, and food delivery", "color": "#fca5a5", "icon": "utensils"},
    {"name": "Friends", "description": "Friend transfers, shared spends, and repayments", "color": "#67e8f9", "icon": "users"},
    {"name": "Laundry", "description": "Laundry and cleaning services", "color": "#cbd5e1", "icon": "shirt"},
    {"name": "Healthcare", "description": "Medical, pharmacy, and wellness expenses", "color": "#6ee7b7", "icon": "heart-pulse"},
    {"name": "Investments", "description": "Investments and portfolio transactions", "color": "#a5b4fc", "icon": "trending-up"},
    {"name": "Transport", "description": "Fuel, taxi, metro, bus, and commute spends", "color": "#7dd3fc", "icon": "bus"},
    {"name": "Rent", "description": "Rent, housing, and recurring accommodation costs", "color": "#d8b4fe", "icon": "home"},
    {"name": "Salary", "description": "Salary and regular income", "color": "#bbf7d0", "icon": "wallet"},
    {"name": "Groceries", "description": "Grocery and household essentials", "color": "#bef264", "icon": "shopping-basket"},
    {"name": "Shopping", "description": "Retail purchases and online shopping", "color": "#fdba74", "icon": "shopping-bag"},
    {"name": "Travel", "description": "Trips, flights, hotels, and travel spends", "color": "#bae6fd", "icon": "plane"},
    {"name": "Other", "description": "Unclassified transactions", "color": "#cbd5e1", "icon": "circle-help"},
    {"name": "Needs Review", "description": "Low-confidence transactions waiting for review", "color": "#fda4af", "icon": "alert-circle"},
]

VISIBLE_CATEGORY_ORDER = [
    "Debt Cleared",
    "Refunds",
    "Bills",
    "Subscriptions",
    "Education",
    "Entertainment",
    "Food",
    "Friends",
    "Laundry",
    "Healthcare",
    "Investments",
    "Transport",
    "Rent",
    "Salary",
    "Groceries",
    "Shopping",
    "Travel",
    "Other",
]


def seed_default_categories(db: Session) -> None:
    """Create or enrich the default category catalog."""
    existing_by_name = {category.name: category for category in db.query(Category).all()}
    changed = False

    for definition in DEFAULT_CATEGORY_DEFINITIONS:
        category = existing_by_name.get(definition["name"])
        if category is None:
            db.add(Category(**definition))
            changed = True
            continue

        for field in ("description", "color", "icon"):
            if not getattr(category, field):
                setattr(category, field, definition[field])
                changed = True

    if changed:
        db.commit()


def get_visible_categories(db: Session) -> list[Category]:
    """Return user-facing categories in the product order."""
    categories = db.query(Category).filter(Category.name.in_(VISIBLE_CATEGORY_ORDER)).all()
    category_by_name = {category.name: category for category in categories}
    return [category_by_name[name] for name in VISIBLE_CATEGORY_ORDER if name in category_by_name]


def validate_category_name(name: str) -> str:
    """Normalize and validate a category name from API input."""
    normalized = name.strip()
    if not normalized:
        raise ValueError("Category name is required.")
    return normalized


def create_category(db: Session, category_data: CategoryCreate) -> Category:
    """Create a category after validating uniqueness."""
    category_name = validate_category_name(category_data.name)
    existing = db.query(Category).filter(Category.name == category_name).first()
    if existing:
        raise ValueError(f"Category '{category_name}' already exists.")

    category = Category(
        name=category_name,
        description=category_data.description,
        color=category_data.color,
        icon=category_data.icon,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
