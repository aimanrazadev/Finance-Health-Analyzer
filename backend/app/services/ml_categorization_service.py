from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.models import Category, CategoryCorrection, Transaction

MIN_TRAINING_LABELS = 20
MODEL_DIR = Path(__file__).resolve().parents[1] / "ml_models"


def _training_rows(db: Session, user_id: int) -> list[tuple[str, str]]:
    correction_rows = (
        db.query(CategoryCorrection, Category)
        .join(Category, CategoryCorrection.new_category_id == Category.id)
        .filter(CategoryCorrection.user_id == user_id)
        .all()
    )
    rows = [
        (correction.original_description or correction.merchant or "", category.name)
        for correction, category in correction_rows
        if correction.original_description or correction.merchant
    ]

    transaction_rows = (
        db.query(Transaction, Category)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.category_id.isnot(None),
            Transaction.categorization_method.in_(("manual", "rule_based", "learned")),
            Transaction.category_confidence >= 0.80,
        )
        .all()
    )
    rows.extend(
        (transaction.description, category.name)
        for transaction, category in transaction_rows
        if transaction.description
    )
    return rows


@lru_cache(maxsize=128)
def _train_cached(user_id: int, labels_signature: tuple[tuple[str, str], ...]):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    texts = [text for text, _label in labels_signature]
    labels = [label for _text, label in labels_signature]
    model = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )
    model.fit(texts, labels)
    return model


def train_user_category_model(db: Session, user_id: int):
    """Train a user-specific classifier when enough corrected labels exist."""
    rows = _training_rows(db, user_id)
    if len(rows) < MIN_TRAINING_LABELS:
        return None
    model = _train_cached(user_id, tuple(rows))
    save_trained_model(user_id, model)
    return model


def _model_path(user_id: int) -> Path:
    return MODEL_DIR / f"user_{user_id}_category_model.joblib"


def save_trained_model(user_id: int, model) -> Path:
    """Persist the trained model so it can be reused after backend restart."""
    import joblib

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = _model_path(user_id)
    joblib.dump(model, path)
    return path


def load_trained_model(user_id: int):
    """Load a previously trained user model from disk if it exists."""
    import joblib

    path = _model_path(user_id)
    if not path.exists():
        return None
    return joblib.load(path)


def predict_category_with_ml(db: Session, user_id: int, description: str) -> tuple[str | None, float]:
    """Predict category name and probability from the user-specific ML model."""
    model = load_trained_model(user_id) or train_user_category_model(db, user_id)
    if model is None:
        return None, 0.0

    probabilities = model.predict_proba([description])[0]
    best_index = int(probabilities.argmax())
    return str(model.classes_[best_index]), float(probabilities[best_index])


def get_model_confidence(db: Session, user_id: int, description: str) -> float:
    _category_name, confidence = predict_category_with_ml(db, user_id, description)
    return confidence


def retrain_after_correction(user_id: int) -> None:
    """Clear cached model so the next prediction trains from the latest labels."""
    _train_cached.cache_clear()
    path = _model_path(user_id)
    if path.exists():
        path.unlink()
