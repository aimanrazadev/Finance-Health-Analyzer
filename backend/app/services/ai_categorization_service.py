import json

from app.ai.llm_client import LLMClient


ALLOWED_AI_CATEGORIES = [
    "Refunds",
    "Bills",
    "Subscriptions",
    "Education",
    "Entertainment",
    "Food",
    "Laundry",
    "Healthcare",
    "Investments",
    "Salary",
    "Groceries",
    "Shopping",
    "Travel",
    "Other",
]


def suggest_category_with_ai(description: str, merchant: str | None, transaction_type: str | None) -> tuple[str | None, float]:
    """Use AI only as a final fallback after learned/rule/ML checks are exhausted."""
    client = LLMClient()
    if not client.is_configured:
        return None, 0.0

    prompt = f"""
Classify this bank transaction into exactly one category from this list:
{", ".join(ALLOWED_AI_CATEGORIES)}

Transaction:
description: {description}
merchant: {merchant or ""}
transaction_type: {transaction_type or ""}

Return only JSON:
{{"category": "Food", "confidence": 0.72}}
Confidence must be between 0 and 1.
"""
    response = client.generate_text(prompt)
    if not response:
        return None, 0.0

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        payload = json.loads(response[start:end])
        category = str(payload.get("category") or "").strip()
        confidence = float(payload.get("confidence") or 0)
    except Exception:
        return None, 0.0

    if category not in ALLOWED_AI_CATEGORIES:
        return None, 0.0
    return category, max(0.0, min(confidence, 1.0))
