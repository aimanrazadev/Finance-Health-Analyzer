from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Category, CategoryLearningRule, UserLearning
from app.services.learning_service import create_or_update_learning_rule, increment_rule_usage
from app.services.merchant_extractor_service import extract_transaction_merchant, normalize_merchant_name
from app.services.ml_categorization_service import predict_category_with_ml

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None
    from difflib import SequenceMatcher


CATEGORY_KEYWORDS = {
    "Food": [
        "albaik", "bakery", "burger", "cafe", "coffee", "delivery", "diner",
        "doordash", "eatsure", "food", "grocery", "kfc", "mcdonald", "pizza",
        "burrito", "dhaba", "eatsure", "rebel", "restaurant", "starbucks",
        "supermarket", "zomato", "swiggy", "toing",
    ],
    "Transport": [
        "bus", "careem", "dmrc", "rapido", "fuel", "gas", "metro", "ola", "parking",
        "petrol", "roppen transpor", "taxi", "train", "transport", "uber",
    ],
    "Travel": [
        "airline", "booking", "flight", "hotel", "makemytrip", "trip", "travel",
    ],
    "Shopping": [
        "amazon", "boutique", "clothes", "fashion", "mall", "noon", "retail",
        "shein", "shopping", "store", "zara", "flipkart",
    ],
    "Groceries": [
        "blinkit", "digi haat", "grocery", "marketpla", "supermarket", "zepto",
    ],
    "Bills": [
        "bill", "electric", "electricity", "internet", "mobile", "phone", "stc",
        "recharge", "utility", "water", "wifi",
    ],
    "Laundry": [
        "laundry", "dry clean", "wash iron",
    ],
    "Subscriptions": [
        "apple music", "netflix", "prime", "spotify", "subscription", "youtube",
    ],
    "Salary": [
        "bonus", "credit", "deposit", "monthly expenses", "payroll", "received",
        "salary", "wage", "interest", "int.pd",
    ],
    "Investments": [
        "iccl", "indian clearing", "investment", "mutual fund", "sip", "zerodha",
    ],
    "Savings": [
        "emergency fund", "fixed deposit", "recurring deposit", "savings", "savings transfer",
    ],
    "Refunds": [
        "cashback", "refund", "reversal",
    ],
}

DEFAULT_CATEGORY_NAME = "Other"
AUTO_SAVE_CONFIDENCE_THRESHOLD = 0.95
SUGGESTION_CONFIDENCE_THRESHOLD = 0.60
ML_AUTO_ASSIGN_CONFIDENCE_THRESHOLD = 0.80


def normalize_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def predict_category_name(description: str, merchant: Optional[str] = None) -> str:
    searchable_text = f"{normalize_text(description)} {normalize_text(merchant)}"

    for category_name, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in searchable_text for keyword in keywords):
            return category_name

    return DEFAULT_CATEGORY_NAME


def _keyword_prediction(description: str, merchant: Optional[str] = None) -> tuple[str, float]:
    searchable_text = f"{normalize_text(description)} {normalize_text(merchant)}"
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in searchable_text:
                confidence = 0.85 if len(keyword) >= 4 else 0.60
                return category_name, confidence
    return DEFAULT_CATEGORY_NAME, 0.30


def _get_category_result(
    db: Session,
    category_name: str,
    confidence: float,
    method: str,
    merchant: Optional[str],
) -> dict[str, object]:
    category = get_category_by_name(db, category_name)
    if method == "needs_review" or confidence < SUGGESTION_CONFIDENCE_THRESHOLD:
        return {
            "category_id": None,
            "category_name": "Uncategorized",
            "suggested_category_id": category.id if category else None,
            "suggested_category_name": category_name,
            "confidence": confidence,
            "method": "needs_review",
            "merchant": merchant,
            "review_status": "needs_review",
            "requires_confirmation": True,
        }

    return {
        "category_id": category.id if category else None,
        "category_name": category_name,
        "suggested_category_id": category.id if category else None,
        "suggested_category_name": category_name,
        "confidence": confidence,
        "method": method,
        "merchant": merchant,
        "review_status": "approved",
        "requires_confirmation": False,
    }


def _learned_rule_prediction(
    db: Session,
    user_id: Optional[int],
    merchant: Optional[str],
) -> tuple[Optional[CategoryLearningRule], float, str]:
    if user_id is None or not merchant:
        return None, 0.0, "needs_review"

    normalized_merchant = normalize_merchant_name(merchant)
    if not normalized_merchant:
        return None, 0.0, "needs_review"

    exact_rule = (
        db.query(CategoryLearningRule)
        .filter(
            CategoryLearningRule.user_id == user_id,
            CategoryLearningRule.normalized_merchant == normalized_merchant,
        )
        .first()
    )
    if exact_rule:
        increment_rule_usage(db, exact_rule)
        return exact_rule, 1.0, "learned"

    rules = db.query(CategoryLearningRule).filter(CategoryLearningRule.user_id == user_id).all()
    best_rule = None
    best_score = 0.0
    for rule in rules:
        if fuzz:
            score = fuzz.ratio(normalized_merchant, rule.normalized_merchant) / 100
        else:
            score = SequenceMatcher(None, normalized_merchant, rule.normalized_merchant).ratio()
        if score > best_score:
            best_score = score
            best_rule = rule

    if best_rule and best_score >= 0.78:
        increment_rule_usage(db, best_rule)
        return best_rule, 0.90, "learned"

    return None, 0.0, "needs_review"


def categorize_transaction(
    db: Session,
    user_id: Optional[int],
    description: str,
    amount: Optional[float] = None,
    transaction_type: Optional[str] = None,
    merchant: Optional[str] = None,
) -> dict[str, object]:
    """Categorize with learned user rules, keyword rules, ML, then Needs Review."""
    extracted_merchant = extract_transaction_merchant(description, merchant)

    learned_rule, learned_confidence, learned_method = _learned_rule_prediction(db, user_id, extracted_merchant)
    if learned_rule:
        category = db.query(Category).filter(Category.id == learned_rule.category_id).first()
        return _get_category_result(
            db,
            category.name if category else DEFAULT_CATEGORY_NAME,
            learned_confidence,
            learned_method,
            extracted_merchant,
        )

    keyword_category, keyword_confidence = _keyword_prediction(description, extracted_merchant)
    if keyword_confidence >= SUGGESTION_CONFIDENCE_THRESHOLD:
        return _get_category_result(db, keyword_category, keyword_confidence, "rule_based", extracted_merchant)

    if user_id is not None:
        ml_category_name, ml_confidence = predict_category_with_ml(db, user_id, description)
        if ml_category_name and ml_confidence >= ML_AUTO_ASSIGN_CONFIDENCE_THRESHOLD:
            return _get_category_result(db, ml_category_name, ml_confidence, "ml_model", extracted_merchant)
        if ml_category_name:
            return _get_category_result(db, ml_category_name, ml_confidence, "needs_review", extracted_merchant)

    if transaction_type == "income" and any(term in normalize_text(description) for term in ["received", "salary", "deposit"]):
        return _get_category_result(db, "Salary", 0.85, "rule_based", extracted_merchant)

    return _get_category_result(db, DEFAULT_CATEGORY_NAME, 0.30, "needs_review", extracted_merchant)


def get_category_by_name(db: Session, name: str) -> Optional[Category]:
    return db.query(Category).filter(Category.name == name).first()


def get_predicted_category_id(
    db: Session,
    description: str,
    merchant: Optional[str] = None,
    user_id: Optional[int] = None,
    amount: Optional[float] = None,
    transaction_type: Optional[str] = None,
) -> Optional[int]:
    result = categorize_transaction(db, user_id, description, amount, transaction_type, merchant)
    return result["category_id"] if isinstance(result["category_id"], int) else None


def learn_user_category_preference(
    db: Session,
    user_id: int,
    merchant: Optional[str],
    category_id: Optional[int],
) -> None:
    normalized_merchant = normalize_text(merchant)
    if not normalized_merchant or category_id is None:
        return

    create_or_update_learning_rule(db, user_id, merchant, category_id)

    existing = (
        db.query(UserLearning)
        .filter(
            UserLearning.user_id == user_id,
            UserLearning.merchant == normalized_merchant,
            UserLearning.category_id == category_id,
        )
        .first()
    )

    if existing:
        existing.frequency += 1
        return

    db.add(
        UserLearning(
            user_id=user_id,
            merchant=normalized_merchant,
            category_id=category_id,
            confidence=1.0,
        )
    )
