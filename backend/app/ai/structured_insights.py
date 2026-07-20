import json
import re
from pydantic import ValidationError
from app.schemas.schemas import AIFinancialContext,AIInsightsContent

def build_fallback_content(context:AIFinancialContext)->AIInsightsContent:
    m,t=context.core_metrics,context.trends;c=context.top_categories[0] if context.top_categories else None;merchant=context.top_merchants[0] if context.top_merchants else None
    spending=[f"Lifestyle expenses totaled INR {m.lifestyle_expenses:,.2f} this period."]
    if t.expense_change_percentage is not None:
        d="increased" if t.expense_change_percentage>0 else "decreased";spending.append(f"Lifestyle spending {d} by {abs(t.expense_change_percentage):.1f}% compared with last period.")
    if c:spending.append(f"{c.name} was the highest spending category at {c.percentage:.1f}%.")
    savings=[f"You saved or invested INR {m.total_savings:,.2f} this period."]
    if m.savings_rate is not None:savings.append(f"Your savings rate was {m.savings_rate:.1f}% of available funds.")
    merchants=["No merchant spending was recorded for this period."] if not merchant else [f"{merchant.name} was your highest-spending merchant at INR {merchant.total:,.2f}.",f"{merchant.name} appeared in {merchant.transaction_count} transaction(s)."]
    subscriptions=[f"{context.subscriptions.count} subscription merchant(s) were found in categorized payments.",f"Their estimated monthly total is INR {context.subscriptions.monthly_total:,.2f}."]
    health=[f"Your Financial Health Score is {context.health_score.overall_score}/100 ({context.health_score.status}).",f"Savings allocation contributed {context.health_score.components.savings_score}/100 to its component score.",f"Spending stability contributed {context.health_score.components.spending_stability_score}/100 to its component score."]
    summary_parts=[f"Your financial health for {context.period_label} is {context.health_score.status}."]
    if c:
        summary_parts.append(f"{c.name} was your largest spending area at {c.percentage:.1f}% of lifestyle spending.")
    elif m.savings_rate is not None:
        summary_parts.append(f"You saved or invested {m.savings_rate:.1f}% of the money available this period.")
    return AIInsightsContent(summary=" ".join(summary_parts),spending_insights=spending[:4],savings_insights=savings[:4],merchant_insights=merchants[:4],subscription_insights=subscriptions[:4],health_insights=health[:4])

def _context_numbers(value) -> list[float]:
    if isinstance(value, dict):
        return [number for item in value.values() for number in _context_numbers(item)]
    if isinstance(value, list):
        return [number for item in value for number in _context_numbers(item)]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [float(value)]
    return []


def validate_llm_content(raw_text:str|None, context:AIFinancialContext|None=None)->AIInsightsContent|None:
    if not raw_text:return None
    cleaned=raw_text.strip()
    if cleaned.startswith("```"):cleaned=cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        content = AIInsightsContent.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError,ValidationError,TypeError):
        return None
    if context is not None:
        context_values = _context_numbers(context.model_dump(mode="json"))
        allowed = context_values + [abs(number) for number in context_values] + [100.0]
        rendered = json.dumps(content.model_dump(), ensure_ascii=True)
        claimed = [float(token.replace(",", "")) for token in re.findall(r"(?<![A-Za-z])-?\d[\d,]*(?:\.\d+)?", rendered)]
        for number in claimed:
            if not any(abs(number - expected) <= max(0.01, abs(expected) * 0.0001) for expected in allowed):
                return None
    return content
