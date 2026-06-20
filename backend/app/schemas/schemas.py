"""Pydantic schemas for the focused Finance Health Analyzer API."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ==================== Authentication Schemas ====================

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: int
    email: str


class MessageResponse(BaseModel):
    message: str


# ==================== Phase 2 Shared Schemas ====================

class ImportProfileCreate(BaseModel):
    profile_name: str = Field(..., min_length=1, max_length=150)
    bank_name: Optional[str] = None
    file_type: Optional[str] = None
    header_signature: str
    column_mapping: dict[str, str]
    preferences: dict[str, Any] = {}
    confidence_score: float = 0


class ImportProfileResponse(BaseModel):
    id: int
    user_id: int
    profile_name: str
    bank_name: Optional[str]
    file_type: Optional[str]
    header_signature: str
    column_mapping: dict[str, str]
    preferences: dict[str, Any] = {}
    confidence_score: float
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime


class MerchantResponse(BaseModel):
    id: int
    user_id: int
    canonical_name: str
    normalized_name: str
    aliases: List[str] = []
    transaction_count: int = 0
    total_spent: float = 0
    last_seen_at: Optional[datetime] = None


class MerchantRenameRequest(BaseModel):
    canonical_name: str = Field(..., min_length=1, max_length=150)


class MerchantMergeRequest(BaseModel):
    source_merchant_id: int


class MerchantDirectoryDetailResponse(BaseModel):
    merchant: MerchantResponse
    total_income: float = 0
    total_expenses: float = 0
    transaction_count: int = 0
    average_amount: float = 0
    transactions: List["TransactionResponse"] = []


class FinancialSnapshotResponse(BaseModel):
    month: int
    year: int
    current_month_spending: float
    projected_month_end_spending: float
    projected_month_end_savings: float
    projected_savings_rate: float
    budget_health: str
    top_merchant: Optional[str]
    top_category: Optional[str]
    alerts: List[str] = []


class AdvisorActionRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=800)


class AdvisorActionResponse(BaseModel):
    action_type: str
    intent: str
    filters: dict[str, Any] = {}
    message: str
    transactions: List["TransactionResponse"] = []
    report: dict[str, Any] = {}


# ==================== Transaction Schemas ====================

class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0)
    category_id: Optional[int] = None
    description: str = Field(..., min_length=1, max_length=255)
    merchant: Optional[str] = None
    transaction_type: str = Field(..., pattern="^(income|expense|savings)$")
    date: datetime


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    category_id: Optional[int]
    friend_id: Optional[int] = None
    merchant_id: Optional[int] = None
    description: str
    merchant: Optional[str]
    extracted_merchant: Optional[str] = None
    normalized_friend_name: Optional[str] = None
    transaction_type: str
    date: datetime
    category_confidence: Optional[float] = None
    categorization_method: Optional[str] = None
    review_status: Optional[str] = None
    is_friend_transaction: Optional[bool] = False
    is_needs_review: Optional[bool] = False
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionCategoryCorrectionRequest(BaseModel):
    category_id: int


# ==================== Friends Schemas ====================

class FriendCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)


class FriendUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)


class FriendResponse(BaseModel):
    id: int
    user_id: int
    name: str
    normalized_name: str
    transaction_count: int = 0
    total_amount: float = 0
    last_transaction_at: Optional[datetime] = None
    is_hidden: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class FriendCreateResponse(BaseModel):
    friend: FriendResponse
    linked_transactions: int
    message: str


class FriendDetailResponse(BaseModel):
    friend: FriendResponse
    transactions: List[TransactionResponse] = []


class FriendDashboardResponse(BaseModel):
    active_friends: int
    linked_transactions: int
    friends: List[FriendResponse] = []


# ==================== Category + Categorization Schemas ====================

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: Optional[str]
    icon: Optional[str]

    class Config:
        from_attributes = True


class CategorizationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    merchant: Optional[str] = None


class CategorizationResponse(BaseModel):
    category_name: str
    category_id: Optional[int]
    suggested_category_id: Optional[int] = None
    suggested_category_name: Optional[str] = None
    confidence: float = 0.30
    method: str = "needs_review"
    merchant: Optional[str] = None
    requires_confirmation: bool = False


class CategoryCorrectionRequest(BaseModel):
    transaction_id: int
    new_category_id: int


class BulkCategoryCorrectionItem(BaseModel):
    transaction_id: int
    new_category_id: int


class BulkCategoryCorrectionRequest(BaseModel):
    corrections: List[BulkCategoryCorrectionItem]


class CategoryCorrectionResponse(BaseModel):
    transaction_id: int
    old_category_id: Optional[int]
    new_category_id: int
    merchant_name: Optional[str]
    message: str


class BulkCategoryCorrectionResponse(BaseModel):
    updated_count: int
    message: str


class CategoryLearningRuleResponse(BaseModel):
    id: int
    user_id: int
    merchant_pattern: str
    merchant_name: Optional[str] = None
    normalized_merchant: str
    category_id: int
    category_name: Optional[str] = None
    confidence_score: float
    times_used: int
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryLearningRuleUpdate(BaseModel):
    merchant_name: Optional[str] = None
    category_id: Optional[int] = None


class CategoryRetrainResponse(BaseModel):
    trained: bool
    label_count: int
    message: str


# ==================== Dashboard Analytics Schemas ====================

class DashboardMetric(BaseModel):
    label: str
    value: float


class CategoryBreakdownItem(BaseModel):
    category_id: Optional[int]
    category_name: str
    total: float
    color: Optional[str] = None


class DashboardSummary(BaseModel):
    month: int
    year: int
    total_income: float
    total_expenses: float
    account_balance: float = 0
    investment_amount: float = 0
    remaining_money: float = 0
    total_savings: float
    investment_savings: float = 0
    remaining_balance_savings: float = 0
    effective_savings: float = 0
    savings_rate: float
    effective_savings_rate: float = 0
    monthly_savings_trend: float = 0
    savings_status: str = "Poor"
    transaction_count: int
    top_category: Optional[str]
    top_merchant: Optional[str] = None
    recurring_subscription_count: int = 0
    recurring_subscription_total: float = 0
    financial_health_score: int = 0
    financial_health_status: str = "Needs Improvement"
    financial_health_reason: str = ""
    budget_health_score: int = 0
    category_breakdown: List[CategoryBreakdownItem]


class DashboardInsightItem(BaseModel):
    title: str
    message: str
    severity: str = "neutral"


class DashboardInsightsResponse(BaseModel):
    month: int
    year: int
    insights: List[DashboardInsightItem]


class ChartDataPoint(BaseModel):
    name: str
    value: float
    color: Optional[str] = None


class IncomeExpenseChart(BaseModel):
    income: float
    expenses: float


class MonthlySpendingPoint(BaseModel):
    month: str
    expenses: float


class MonthlyTrendPoint(BaseModel):
    month: str
    income: float
    expenses: float
    savings: float
    investments: float


class MonthlyTrendResponse(BaseModel):
    year: int
    trends: List[MonthlyTrendPoint]
    income_change_percentage: Optional[float] = None
    expense_change_percentage: Optional[float] = None
    savings_change_percentage: Optional[float] = None
    investment_change_percentage: Optional[float] = None


class DashboardChartsResponse(BaseModel):
    month: int
    year: int
    category_breakdown: List[ChartDataPoint]
    income_vs_expense: IncomeExpenseChart
    monthly_spending: List[MonthlySpendingPoint]
    monthly_trends: List[MonthlyTrendPoint] = []
    top_merchants: List[ChartDataPoint]


class SavingsAnalyticsResponse(BaseModel):
    month: int
    year: int
    savings: float
    savings_rate: float
    monthly_savings_trend: float
    previous_month_savings: float
    savings_status: str


class CategoryAnalyticsItem(BaseModel):
    category_id: Optional[int]
    category_name: str
    total: float
    percentage: float
    transaction_count: int
    color: Optional[str] = None


class CategoryAnalyticsResponse(BaseModel):
    month: int
    year: int
    total_expenses: float
    highest_spending_category: Optional[str]
    categories: List[CategoryAnalyticsItem]


class MerchantAnalyticsItem(BaseModel):
    merchant_name: str
    total_spent: float
    transaction_count: int
    frequency: int
    average_amount: float


class MerchantAnalyticsResponse(BaseModel):
    month: int
    year: int
    top_merchants: List[MerchantAnalyticsItem]
    most_frequent_merchants: List[MerchantAnalyticsItem]
    highest_spending_merchants: List[MerchantAnalyticsItem]


class SubscriptionAnalyticsItem(BaseModel):
    id: Optional[int] = None
    merchant_name: str
    amount: float
    billing_period: str = "monthly"
    monthly_cost: float
    transaction_count: int
    confidence: float
    next_expected_payment: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionAnalyticsResponse(BaseModel):
    month: int
    year: int
    subscription_count: int
    total_monthly_cost: float
    subscriptions: List[SubscriptionAnalyticsItem]


class DashboardDataResponse(BaseModel):
    summary: DashboardSummary
    savings: SavingsAnalyticsResponse
    categories: CategoryAnalyticsResponse
    merchants: MerchantAnalyticsResponse
    subscriptions: SubscriptionAnalyticsResponse
    charts: DashboardChartsResponse
    insights: DashboardInsightsResponse


# ==================== Upload Schemas ====================

class UploadPreviewRow(BaseModel):
    row_number: int
    transaction_date: datetime
    date: Optional[datetime] = None
    description: str
    reference_no: Optional[str] = None
    withdrawal_amount: Optional[float] = None
    deposit_amount: Optional[float] = None
    balance: Optional[float] = None
    amount: float
    transaction_type: str
    source: str = "manual"
    merchant: Optional[str] = None
    merchant_name: Optional[str] = None
    extracted_merchant: Optional[str] = None
    category_id: Optional[int] = None
    category: Optional[str] = None
    category_name: Optional[str] = None
    suggested_category_id: Optional[int] = None
    suggested_category_name: Optional[str] = None
    category_confidence: Optional[float] = None
    categorization_method: Optional[str] = None
    review_status: Optional[str] = None
    is_needs_review: Optional[bool] = False
    requires_confirmation: bool = False


class UploadFailedItem(BaseModel):
    row_number: Optional[int] = None
    raw_data: Any
    error: str


class UploadPreviewResponse(BaseModel):
    file_name: str
    file_size: int
    file_type: str
    import_profile_id: Optional[int] = None
    import_profile_name: Optional[str] = None
    import_confidence: float = 0
    column_mapping: dict[str, str] = {}
    total_rows: int
    successful_rows: int
    valid_rows: int
    failed_rows: int
    rows: List[UploadPreviewRow]
    failed_items: List[UploadFailedItem] = []
    errors: List[str]


class UploadConfirmRequest(BaseModel):
    file_name: str
    file_size: int
    file_type: Optional[str] = None
    bank_name: Optional[str] = None
    column_mapping: dict[str, str] = {}
    total_rows: Optional[int] = None
    failed_rows: Optional[int] = None
    rows: List[UploadPreviewRow]


class UploadConfirmResponse(BaseModel):
    uploaded_file_id: int
    saved_transactions: int
    skipped_duplicates: int = 0
    message: str


class UploadedFileResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_path: str
    file_size: int
    file_type: Optional[str] = None
    upload_status: Optional[str] = None
    total_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    transaction_count: int
    upload_date: datetime

    class Config:
        from_attributes = True


# ==================== AI Advisor Schemas ====================

class AiInsightResponse(BaseModel):
    id: int
    user_id: int
    insight_text: str
    insight_type: str
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True


class AiInsightsResponse(BaseModel):
    month: int
    year: int
    insights: List[AiInsightResponse]


class AdvisorAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=800)
    chat_id: Optional[int] = None
    month: Optional[int] = Field(default=None, ge=1, le=12)
    year: Optional[int] = Field(default=None, ge=2000, le=2100)


class AdvisorRecommendationItem(BaseModel):
    title: str
    reason: str
    impact: str
    estimated_savings: float = 0
    category: Optional[str] = None


class AdvisorStructuredResponse(BaseModel):
    summary: str
    main_problem: str
    recommendations: List[AdvisorRecommendationItem] = []
    savings_impact: Optional[str] = None
    subscriptions: List[str] = []
    risk_note: str = "This is budgeting guidance, not investment, tax, or legal advice."


class AdvisorMessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdvisorChatCreate(BaseModel):
    title: Optional[str] = None


class AdvisorChatResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdvisorChatDetailResponse(AdvisorChatResponse):
    messages: List[AdvisorMessageResponse] = []


class AdvisorRecommendationResponse(BaseModel):
    id: int
    user_id: int
    chat_id: int
    title: str
    description: Optional[str] = None
    estimated_savings: float = 0
    category: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdvisorRecommendationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|accepted|dismissed|completed)$")


class AdvisorAskResponse(BaseModel):
    chat: AdvisorChatResponse
    user_message: AdvisorMessageResponse
    assistant_message: AdvisorMessageResponse
    response: AdvisorStructuredResponse
    recommendations: List[AdvisorRecommendationResponse] = []
    intent: str
    context: dict[str, Any]


# ==================== Financial Health Score Schemas ====================

class FinancialHealthBreakdownItem(BaseModel):
    label: str
    score: int
    status: str
    description: str


class FinancialHealthScoreResponse(BaseModel):
    id: int
    month: int
    year: int
    overall_score: int
    status_label: str
    savings_score: int
    budget_score: int
    stability_score: int
    subscription_score: int
    debt_score: int
    emergency_fund_score: int
    breakdown: List[FinancialHealthBreakdownItem]
    improvement_tips: List[str]
    calculated_at: datetime
