import json

from app.schemas.schemas import AIFinancialContext


SYSTEM_RULES = """You are the explanation layer of a personal finance analyzer.
Use only the supplied verified analytics.
Do not invent or recalculate any number.
Do not describe the user as rich, poor, safe, or unsafe.
Do not provide investment, tax, or legal advice.
Give practical budgeting and spending guidance only.
Use short sentences and common, everyday words.
Recommendations must directly relate to an insight and name a clear action.
Return valid JSON only, with no markdown fences or commentary."""


def build_insights_prompt(
    context: AIFinancialContext,
) -> str:
    response_shape = {
        "summary": "string",
        "spending_insights": ["string"],
        "savings_insights": ["string"],
        "merchant_insights": ["string"],
        "subscription_insights": ["string"],
        "health_insights": ["string"],
        "recommendations": [
            {"priority": 1, "title": "string", "reason": "string", "action": "string", "focus": "string"}
        ],
    }
    return (
        f"{SYSTEM_RULES}\n\n"
        "Explain the supplied analytics in simple language. Return 2-4 concise items per insight group and 3-5 ranked recommendations. "
        "Keep all supplied numbers exact. Return this exact JSON shape:\n"
        f"{json.dumps(response_shape, ensure_ascii=True)}\n\n"
        "SUPPLIED DATA:\n"
        f"{json.dumps(context.model_dump(mode='json'), ensure_ascii=True, separators=(',', ':'))}"
    )
