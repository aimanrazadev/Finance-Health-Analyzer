import json
import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.ai.llm_client import LLMClient
from app.models.models import AdvisorChat, AdvisorMessage, AdvisorRecommendation, Transaction
from app.schemas.schemas import AdvisorStructuredResponse
from app.services.financial_analytics_service import (
    build_category_analytics,
    build_merchant_analytics_detail,
    build_savings_analytics,
    build_subscription_analytics,
)
from app.services.dashboard_summary_service import build_dashboard_summary
from app.services.financial_health_service import calculate_financial_health_score


RELATED_KEYWORDS = {
    "save", "saving", "savings", "spend", "spending", "expense", "expenses",
    "overspend", "overspending", "subscription", "subscriptions", "health",
    "score", "merchant", "category", "budget", "money", "income", "food",
    "shopping", "transport", "finance", "financial",
}


def detect_advisor_intent(question: str) -> str:
    """Classify the question so retrieval stays focused and explainable."""
    text = question.lower()
    if any(term in text for term in ("subscription", "netflix", "spotify", "prime")):
        return "subscription_analysis"
    if any(term in text for term in ("health", "score", "improve my score")):
        return "health_score"
    if any(term in text for term in ("overspend", "overspending", "too much", "where am i spending")):
        return "overspending_analysis"
    if any(term in text for term in ("save", "saving", "savings")):
        return "savings_advice"
    if any(term in text for term in ("budget", "limit", "recommendation")):
        return "budget_recommendation"
    return "general_financial_advice"


def is_finance_question(question: str) -> bool:
    tokens = set(re.findall(r"[a-z]+", question.lower()))
    return bool(tokens & RELATED_KEYWORDS)


def build_financial_context(
    db: Session,
    user_id: int,
    question: str,
    month: int | None = None,
    year: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Retrieve compact user-specific analytics from MySQL-backed services."""
    today = date.today()
    selected_month = month or today.month
    selected_year = year or today.year
    intent = detect_advisor_intent(question)

    summary = build_dashboard_summary(db, user_id, selected_month, selected_year)
    savings = build_savings_analytics(db, user_id, selected_month, selected_year)
    context: dict[str, Any] = {
        "period": {"month": selected_month, "year": selected_year},
        "intent": intent,
        "monthly_income": summary.total_income,
        "monthly_expenses": summary.total_expenses,
        "monthly_savings": summary.total_savings,
        "savings_rate": summary.savings_rate,
        "savings_status": summary.savings_status,
        "monthly_savings_trend": savings.monthly_savings_trend,
        "transaction_count": summary.transaction_count,
        "health_score": summary.financial_health_score,
        "health_status": summary.financial_health_status,
        "health_reason": summary.financial_health_reason,
    }

    if intent in {"overspending_analysis", "budget_recommendation", "general_financial_advice", "savings_advice"}:
        categories = build_category_analytics(db, user_id, selected_month, selected_year)
        context["top_categories"] = [
            {
                "category": item.category_name,
                "amount": item.total,
                "percentage": item.percentage,
                "transaction_count": item.transaction_count,
            }
            for item in categories.categories[:5]
        ]

    if intent in {"overspending_analysis", "general_financial_advice", "savings_advice"}:
        merchants = build_merchant_analytics_detail(db, user_id, selected_month, selected_year)
        context["top_merchants"] = [
            {
                "merchant": item.merchant_name,
                "amount": item.total_spent,
                "frequency": item.frequency,
            }
            for item in merchants.top_merchants[:5]
        ]

    if intent in {"subscription_analysis", "general_financial_advice", "savings_advice", "budget_recommendation"}:
        subscriptions = build_subscription_analytics(db, user_id, selected_month, selected_year)
        context["subscriptions"] = [
            {
                "merchant": item.merchant_name,
                "amount": item.monthly_cost,
                "confidence": item.confidence,
            }
            for item in subscriptions.subscriptions[:6]
        ]
        context["subscription_total"] = subscriptions.total_monthly_cost
        context["subscription_count"] = subscriptions.subscription_count

    if intent == "health_score":
        health = calculate_financial_health_score(db, user_id, selected_month, selected_year)
        context["health_breakdown"] = health["breakdown"]
        context["improvement_tips"] = health["improvement_tips"]

    return intent, context


def has_enough_financial_data(context: dict[str, Any]) -> bool:
    return int(context.get("transaction_count") or 0) > 0


def build_advisor_prompt(question: str, context: dict[str, Any]) -> str:
    """Build a strict prompt that asks for JSON and prevents made-up numbers."""
    context_json = json.dumps(context, ensure_ascii=True, indent=2)
    return f"""
You are a helpful financial advisor inside a personal finance app.

Rules:
- Use only the provided financial data.
- Do not invent numbers, categories, merchants, subscriptions, or percentages.
- Do not give investment, tax, legal, loan, or guaranteed-return advice.
- Give practical budgeting and spending suggestions.
- If data is missing, say what data is missing and keep the answer conservative.
- Return only valid JSON. Do not wrap it in markdown.

User question:
{question}

Financial data:
{context_json}

Return JSON with this exact shape:
{{
  "summary": "short summary",
  "main_problem": "main issue found from provided data",
  "recommendations": [
    {{
      "title": "action title",
      "reason": "why this helps using provided data",
      "impact": "expected budgeting impact",
      "estimated_savings": 0,
      "category": "optional category"
    }}
  ],
  "savings_impact": "how savings rate or monthly savings may improve",
  "subscriptions": ["subscription suggestion"],
  "risk_note": "This is budgeting guidance, not investment, tax, or legal advice."
}}
"""


def fallback_advisor_response(question: str, context: dict[str, Any], reason: str = "fallback") -> AdvisorStructuredResponse:
    """Create a deterministic safe answer when LLM output is missing or invalid."""
    if not is_finance_question(question):
        return AdvisorStructuredResponse(
            summary="I can help with budgeting, spending, savings, subscriptions, and financial health questions.",
            main_problem="This question does not look related to your personal finance data.",
            recommendations=[],
            savings_impact="Ask about saving money, overspending, subscriptions, or your health score.",
            subscriptions=[],
            risk_note="This is budgeting guidance, not investment, tax, or legal advice.",
        )

    if not has_enough_financial_data(context):
        return AdvisorStructuredResponse(
            summary="I need at least one month of transaction data to give useful advice.",
            main_problem="No categorized transactions were found for the selected period.",
            recommendations=[],
            savings_impact="Upload or add transactions first, then ask again.",
            subscriptions=[],
            risk_note="This is budgeting guidance, not investment, tax, or legal advice.",
        )

    top_categories = context.get("top_categories") or []
    top_merchants = context.get("top_merchants") or []
    recommendations = []
    if top_categories:
        category = top_categories[0]
        estimated = round(float(category.get("amount") or 0) * 0.15, 2)
        recommendations.append({
            "title": f"Review {category['category']} spending",
            "reason": f"{category['category']} is one of your largest spending areas.",
            "impact": f"Reducing this by 15% could save about INR {estimated:,.0f}.",
            "estimated_savings": estimated,
            "category": category["category"],
        })
    if top_merchants:
        merchant = top_merchants[0]
        estimated = round(float(merchant.get("amount") or 0) * 0.10, 2)
        recommendations.append({
            "title": f"Limit spending at {merchant['merchant']}",
            "reason": f"{merchant['merchant']} is your highest spending merchant in this context.",
            "impact": f"A 10% cut could save about INR {estimated:,.0f}.",
            "estimated_savings": estimated,
            "category": "Merchant",
        })

    subscriptions = [
        f"Review {item['merchant']} at INR {float(item['amount']):,.0f}/month"
        for item in context.get("subscriptions", [])[:3]
    ]
    return AdvisorStructuredResponse(
        summary=(
            f"Income is INR {float(context.get('monthly_income') or 0):,.0f}, "
            f"expenses are INR {float(context.get('monthly_expenses') or 0):,.0f}, "
            f"and savings rate is {float(context.get('savings_rate') or 0):.1f}%."
        ),
        main_problem=context.get("health_reason") or "The biggest opportunity is controlling high spending areas.",
        recommendations=recommendations,
        savings_impact="Small cuts in top categories can improve monthly savings without changing every habit.",
        subscriptions=subscriptions,
        risk_note="This is budgeting guidance, not investment, tax, or legal advice.",
    )


def parse_advisor_response(raw_text: str | None, question: str, context: dict[str, Any]) -> AdvisorStructuredResponse:
    if not raw_text:
        return fallback_advisor_response(question, context, "empty_response")

    try:
        text = raw_text.strip()
        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        payload = json.loads(text[start:end])
        return AdvisorStructuredResponse(
            summary=str(payload.get("summary") or "").strip() or "Here is your financial summary.",
            main_problem=str(payload.get("main_problem") or "").strip() or "No single major issue was detected.",
            recommendations=[
                {
                    "title": str(item.get("title") or "Review spending").strip(),
                    "reason": str(item.get("reason") or "Based on your financial data.").strip(),
                    "impact": str(item.get("impact") or "May improve monthly savings.").strip(),
                    "estimated_savings": float(item.get("estimated_savings") or 0),
                    "category": item.get("category"),
                }
                for item in (payload.get("recommendations") or [])
                if isinstance(item, dict)
            ],
            savings_impact=payload.get("savings_impact"),
            subscriptions=[str(item) for item in (payload.get("subscriptions") or [])],
            risk_note=str(payload.get("risk_note") or "This is budgeting guidance, not investment, tax, or legal advice."),
        )
    except Exception:
        return fallback_advisor_response(question, context, "malformed_json")


def get_or_create_chat(db: Session, user_id: int, chat_id: int | None, question: str) -> AdvisorChat:
    if chat_id:
        chat = db.query(AdvisorChat).filter(AdvisorChat.id == chat_id, AdvisorChat.user_id == user_id).first()
        if chat:
            return chat

    title = question.strip()[:60] or "Advisor chat"
    chat = AdvisorChat(user_id=user_id, title=title)
    db.add(chat)
    db.flush()
    return chat


def save_advisor_message(db: Session, chat_id: int, role: str, content: str) -> AdvisorMessage:
    message = AdvisorMessage(chat_id=chat_id, role=role, content=content)
    db.add(message)
    db.flush()
    return message


def save_advisor_recommendations(
    db: Session,
    user_id: int,
    chat_id: int,
    response: AdvisorStructuredResponse,
) -> list[AdvisorRecommendation]:
    saved: list[AdvisorRecommendation] = []
    for item in response.recommendations:
        record = AdvisorRecommendation(
            user_id=user_id,
            chat_id=chat_id,
            title=item.title,
            description=item.reason,
            estimated_savings=item.estimated_savings,
            category=item.category,
            status="pending",
        )
        db.add(record)
        saved.append(record)
    db.flush()
    return saved


def ask_financial_advisor(
    db: Session,
    user_id: int,
    question: str,
    chat_id: int | None = None,
    month: int | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    intent, context = build_financial_context(db, user_id, question, month, year)
    chat = get_or_create_chat(db, user_id, chat_id, question)
    user_message = save_advisor_message(db, chat.id, "user", question)

    if not is_finance_question(question) or not has_enough_financial_data(context):
        structured = fallback_advisor_response(question, context)
    else:
        prompt = build_advisor_prompt(question, context)
        structured = parse_advisor_response(LLMClient().generate_text(prompt), question, context)

    structured_payload = structured.model_dump() if hasattr(structured, "model_dump") else structured.dict()
    assistant_content = json.dumps(structured_payload, ensure_ascii=True)
    assistant_message = save_advisor_message(db, chat.id, "assistant", assistant_content)
    recommendations = save_advisor_recommendations(db, user_id, chat.id, structured)
    db.commit()

    for item in (chat, user_message, assistant_message, *recommendations):
        db.refresh(item)

    return {
        "chat": chat,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "response": structured,
        "recommendations": recommendations,
        "intent": intent,
        "context": context,
    }
