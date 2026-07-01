from app.schemas.schemas import AIFinancialContext,AIRecommendationItem

def generate_recommendations(context:AIFinancialContext)->list[AIRecommendationItem]:
    items=[];m=context.core_metrics
    if m.savings_rate is None or m.savings_rate<20:items.append(AIRecommendationItem(priority=1,title="Increase your savings",reason=f"Your savings rate is {m.savings_rate or 0:.1f}% for this period.",action="Move a fixed amount to Savings or Investments after income arrives.",focus="Build habit"))
    if context.subscriptions.count:items.append(AIRecommendationItem(priority=2,title="Review subscriptions",reason=f"{context.subscriptions.count} recurring payment(s) total INR {context.subscriptions.monthly_total:,.2f} per month.",action="Cancel or pause recurring services you no longer use.",focus="Reduce unnecessary costs"))
    if context.top_categories:
        c=context.top_categories[0];items.append(AIRecommendationItem(priority=3,title=f"Control {c.name.lower()} spending",reason=f"{c.name} represents {c.percentage:.1f}% of lifestyle spending.",action=f"Review the largest {c.name.lower()} purchases and set a lower target.",focus="Manage categories"))
    items.append(AIRecommendationItem(priority=4,title="Keep your progress going",reason=f"Your financial health score is {context.health_score.overall_score}/100.",action="Review these insights each month and keep the habits that work.",focus="Stay consistent"))
    for i,item in enumerate(items[:4],1):item.priority=i
    return items[:4]
