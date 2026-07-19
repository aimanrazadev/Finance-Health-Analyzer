from functools import lru_cache
from pathlib import Path
from collections import Counter

from sqlalchemy.orm import Session

from app.models.models import Category, CategoryCorrection, Transaction

MIN_TRAINING_LABELS = 20
MODEL_DIR = Path(__file__).resolve().parent / "models"


def _build_model():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )


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
    texts = [text for text, _label in labels_signature]
    labels = [label for _text, label in labels_signature]
    model = _build_model()
    model.fit(texts, labels)
    return model


def evaluate_user_category_model(db: Session, user_id: int, test_size: float = 0.25) -> dict[str, object]:
    """Evaluate the user's categorization model from the same labeled rows used for training.

    Uses a held-out test split when enough labels/classes exist. For very small datasets,
    falls back to training-set accuracy and marks the evaluation as optimistic.
    """
    rows = _training_rows(db, user_id)
    label_count = len(rows)
    labels = [label for _text, label in rows]
    class_counts = Counter(labels)
    class_count = len(class_counts)

    if label_count < MIN_TRAINING_LABELS:
        return {
            "accuracy": None,
            "label_count": label_count,
            "class_count": class_count,
            "evaluation_type": "not_enough_labels",
            "message": f"Need at least {MIN_TRAINING_LABELS} labeled transactions to evaluate the ML model.",
        }

    if class_count < 2:
        return {
            "accuracy": None,
            "label_count": label_count,
            "class_count": class_count,
            "evaluation_type": "not_enough_classes",
            "message": "Need at least two categories in labeled data to evaluate classification accuracy.",
        }

    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split

    texts = [text for text, _label in rows]
    can_stratify = min(class_counts.values()) >= 2 and label_count >= max(8, class_count * 2)
    stratify = labels if can_stratify else None

    if label_count >= 8:
        x_train, x_test, y_train, y_test = train_test_split(
            texts,
            labels,
            test_size=test_size,
            random_state=42,
            stratify=stratify,
        )
        model = _build_model()
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        accuracy = float(accuracy_score(y_test, predictions))
        return {
            "accuracy": round(accuracy, 4),
            "label_count": label_count,
            "class_count": class_count,
            "test_sample_count": len(y_test),
            "evaluation_type": "holdout",
            "message": f"Holdout accuracy is {accuracy * 100:.1f}% on {len(y_test)} test transactions.",
        }

    model = _build_model()
    model.fit(texts, labels)
    predictions = model.predict(texts)
    accuracy = float(accuracy_score(labels, predictions))
    return {
        "accuracy": round(accuracy, 4),
        "label_count": label_count,
        "class_count": class_count,
        "test_sample_count": label_count,
        "evaluation_type": "training_set",
        "message": f"Training-set accuracy is {accuracy * 100:.1f}%; this is optimistic because the labeled dataset is small.",
    }


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


def retrain_after_correction(user_id: int) -> None:
    """Clear cached model so the next prediction trains from the latest labels."""
    _train_cached.cache_clear()
    path = _model_path(user_id)
    if path.exists():
        path.unlink()
