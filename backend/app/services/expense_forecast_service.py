from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.models import Category, ForecastResult, Transaction

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
except Exception:  # pragma: no cover
    LinearRegression = None
    RandomForestRegressor = None


@dataclass
class MonthlyRow:
    month: str
    month_index: int
    income: float
    expenses: float
    transaction_count: int
    category_spending: float = 0.0


def _add_month(year: int, month: int, offset: int = 1) -> tuple[int, int]:
    month_index = (year * 12 + month - 1) + offset
    return month_index // 12, month_index % 12 + 1


def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _collect_monthly_rows(db: Session, user_id: int, category_id: Optional[int] = None) -> list[MonthlyRow]:
    rows = (
        db.query(
            func.year(Transaction.date).label("year"),
            func.month(Transaction.date).label("month"),
            func.coalesce(func.sum(case((Transaction.transaction_type == "income", Transaction.amount), else_=0)), 0).label("income"),
            func.coalesce(func.sum(case((Transaction.transaction_type == "expense", Transaction.amount), else_=0)), 0).label("expenses"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .filter(Transaction.user_id == user_id)
        .group_by(func.year(Transaction.date), func.month(Transaction.date))
        .order_by(func.year(Transaction.date), func.month(Transaction.date))
        .all()
    )

    category_by_month = {}
    if category_id:
        category_rows = (
            db.query(
                func.year(Transaction.date).label("year"),
                func.month(Transaction.date).label("month"),
                func.coalesce(func.sum(Transaction.amount), 0).label("category_spending"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "expense",
                Transaction.category_id == category_id,
            )
            .group_by(func.year(Transaction.date), func.month(Transaction.date))
            .all()
        )
        category_by_month = {
            (int(row.year), int(row.month)): float(row.category_spending or 0)
            for row in category_rows
        }

    return [
        MonthlyRow(
            month=_month_key(int(row.year), int(row.month)),
            month_index=int(row.year) * 12 + int(row.month),
            income=float(row.income or 0),
            expenses=float(row.expenses or 0),
            transaction_count=int(row.transaction_count or 0),
            category_spending=category_by_month.get((int(row.year), int(row.month)), 0.0),
        )
        for row in rows
    ]


def _features_for_rows(rows: list[MonthlyRow], target_key: str = "expenses") -> tuple[list[list[float]], list[float]]:
    features = []
    targets = []
    for index in range(1, len(rows)):
        previous_values = [
            getattr(rows[past_index], target_key)
            for past_index in range(max(0, index - 3), index)
        ]
        previous_month = getattr(rows[index - 1], target_key)
        three_month_average = sum(previous_values) / len(previous_values) if previous_values else previous_month
        current = rows[index]
        features.append([
            previous_month,
            three_month_average,
            current.income,
            current.transaction_count,
            current.category_spending,
            index + 1,
        ])
        targets.append(getattr(current, target_key))
    return features, targets


def _next_features(rows: list[MonthlyRow], category_id: Optional[int] = None) -> list[float]:
    target_key = "category_spending" if category_id else "expenses"
    previous_values = [getattr(row, target_key) for row in rows[-3:]]
    previous_month = previous_values[-1] if previous_values else 0
    three_month_average = sum(previous_values) / len(previous_values) if previous_values else 0
    divisor = min(len(rows), 3) if rows else 1
    recent_income = sum(row.income for row in rows[-3:]) / divisor if rows else 0
    recent_count = sum(row.transaction_count for row in rows[-3:]) / divisor if rows else 0
    recent_category = sum(row.category_spending for row in rows[-3:]) / divisor if rows else 0
    return [previous_month, three_month_average, recent_income, recent_count, recent_category, len(rows) + 1]


def _fit_predict(features: list[list[float]], targets: list[float], next_features: list[float]) -> tuple[float, str, Optional[float]]:
    if not targets:
        return 0.0, "moving_average", None
    if len(targets) < 3 or LinearRegression is None:
        return sum(targets[-3:]) / min(len(targets), 3), "moving_average", None

    linear = LinearRegression()
    linear.fit(features, targets)
    linear_prediction = float(linear.predict([next_features])[0])
    model_used = "linear_regression"
    prediction = linear_prediction

    if len(targets) >= 5 and RandomForestRegressor is not None:
        forest = RandomForestRegressor(n_estimators=80, random_state=42, min_samples_leaf=1)
        forest.fit(features, targets)
        forest_prediction = float(forest.predict([next_features])[0])
        prediction = (linear_prediction + forest_prediction) / 2
        model_used = "linear_regression_random_forest"

    fitted = linear.predict(features)
    errors = [abs(float(actual) - float(predicted)) for actual, predicted in zip(targets, fitted)]
    accuracy = max(0, 100 - ((sum(errors) / len(errors)) / (sum(targets) / len(targets) or 1)) * 100)
    return max(prediction, 0), model_used, round(accuracy, 2)


def _category_forecasts(db: Session, user_id: int) -> list[dict]:
    category_rows = (
        db.query(Transaction.category_id, Category.name, func.coalesce(func.sum(Transaction.amount), 0).label("total"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense")
        .group_by(Transaction.category_id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
        .all()
    )

    forecasts = []
    for row in category_rows:
        if row.category_id is None:
            continue
        monthly_rows = _collect_monthly_rows(db, user_id, row.category_id)
        features, targets = _features_for_rows(monthly_rows, target_key="category_spending")
        prediction, _model, _accuracy = _fit_predict(features, targets, _next_features(monthly_rows, row.category_id))
        forecasts.append({
            "category_id": row.category_id,
            "category_name": row.name or "Uncategorized",
            "predicted_amount": round(prediction, 2),
        })
    return forecasts


def generate_expense_forecast(db: Session, user_id: int) -> dict:
    monthly_rows = _collect_monthly_rows(db, user_id)
    if monthly_rows:
        last_year, last_month = map(int, monthly_rows[-1].month.split("-"))
    else:
        today = date.today()
        last_year, last_month = today.year, today.month

    forecast_year, forecast_month_number = _add_month(last_year, last_month)
    forecast_month = _month_key(forecast_year, forecast_month_number)
    features, targets = _features_for_rows(monthly_rows)
    next_features = _next_features(monthly_rows)
    predicted_amount, model_used, accuracy = _fit_predict(features, targets, next_features)

    recent_targets = targets[-3:] or [row.expenses for row in monthly_rows[-3:]]
    average_error = (
        sum(abs(value - (sum(recent_targets) / len(recent_targets))) for value in recent_targets) / len(recent_targets)
        if recent_targets else predicted_amount * 0.15
    )
    confidence_margin = max(average_error, predicted_amount * 0.12, 250)

    record = ForecastResult(
        user_id=user_id,
        category_id=None,
        forecast_month=forecast_month,
        predicted_amount=round(predicted_amount, 2),
        confidence_lower=round(max(predicted_amount - confidence_margin, 0), 2),
        confidence_upper=round(predicted_amount + confidence_margin, 2),
        model_used=model_used,
        accuracy=accuracy,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    history = [
        {"month": row.month, "actual_expenses": round(row.expenses, 2), "predicted_expenses": None}
        for row in monthly_rows[-12:]
    ]
    history.append({"month": forecast_month, "actual_expenses": 0, "predicted_expenses": round(predicted_amount, 2)})

    return {
        "id": record.id,
        "forecast_month": forecast_month,
        "predicted_amount": record.predicted_amount,
        "confidence_lower": record.confidence_lower,
        "confidence_upper": record.confidence_upper,
        "model_used": record.model_used,
        "accuracy": record.accuracy,
        "feature_summary": {
            "months_used": len(monthly_rows),
            "previous_month_spending": next_features[0],
            "three_month_average": round(next_features[1], 2),
            "average_income": round(next_features[2], 2),
            "average_transaction_count": round(next_features[3], 2),
        },
        "category_forecasts": _category_forecasts(db, user_id),
        "history": history,
        "created_at": record.created_at,
    }
