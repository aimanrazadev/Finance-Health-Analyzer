import json

from app.schemas.schemas import AIFinancialContext


SYSTEM_RULES = """You are the explanation layer of a FInance Health analyzer.
Use only the supplied verified analytics.
Do not invent or recalculate any number or hallucinate.
Do not describe the user as rich, poor, safe, or unsafe.
Do not provide investment, tax, or legal advice.
Give Recommendations to the user according to their spendings
Treat subscription figures as categorized subscription payments; do not claim proven recurrence unless the supplied data proves it.
Use short sentences and common, everyday words.
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
    }
    return (
        f"{SYSTEM_RULES}\n\n"
        "Explain the supplied analytics in simple language. Return 2-4 concise items per insight group. "
        "The summary must be 2-3 useful sentences and no more than 70 words. First state the financial health status naturally. "
        "Then explain the most important reason using one exact supplied figure. "
        "Do not include the numeric health score in the summary, do not put the status in brackets, and do not use vague finance slogans. "
        "Keep all supplied numbers exact. Return this exact JSON shape:\n"
        f"{json.dumps(response_shape, ensure_ascii=True)}\n\n"
        "SUPPLIED DATA:\n"
        f"{json.dumps(context.model_dump(mode='json'), ensure_ascii=True, separators=(',', ':'))}"
    )
