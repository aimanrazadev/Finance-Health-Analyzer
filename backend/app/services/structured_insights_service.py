import json
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
    subscriptions=[f"{context.subscriptions.count} recurring subscription(s) were detected.",f"Recurring subscriptions total INR {context.subscriptions.monthly_total:,.2f} per month."]
    health=[f"Your Financial Health Score is {context.health_score.overall_score}/100 ({context.health_score.status}).",f"Savings allocation contributed {context.health_score.components.savings_score}/100 to its component score.",f"Spending stability contributed {context.health_score.components.spending_stability_score}/100 to its component score."]
    summary_parts=[f"Your financial health for {context.period_label} is {context.health_score.status}."]
    if c:
        summary_parts.append(f"{c.name} was your largest spending area at {c.percentage:.1f}% of lifestyle spending.")
    elif m.savings_rate is not None:
        summary_parts.append(f"You saved or invested {m.savings_rate:.1f}% of the money available this period.")
    return AIInsightsContent(summary=" ".join(summary_parts),spending_insights=spending[:4],savings_insights=savings[:4],merchant_insights=merchants[:4],subscription_insights=subscriptions[:4],health_insights=health[:4])

def validate_llm_content(raw_text:str|None)->AIInsightsContent|None:
    if not raw_text:return None
    cleaned=raw_text.strip()
    if cleaned.startswith("```"):cleaned=cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:return AIInsightsContent.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError,ValidationError,TypeError):return None
