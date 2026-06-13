"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Any, List, Optional


# ==================== Authentication Schemas ====================

class UserRegister(BaseModel):
    """Schema for user registration"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePassword123"
            }
        }


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "password": "SecurePassword123"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response (safe user info without password)"""
    id: int
    name: str
    email: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "name": "John Doe",
                    "email": "john@example.com",
                    "created_at": "2026-06-07T12:00:00",
                    "is_active": True
                }
            }
        }


class TokenData(BaseModel):
    """Schema for JWT token payload"""
    user_id: int
    email: str


# ==================== Transaction Schemas ====================

class TransactionCreate(BaseModel):
    """Schema for creating a transaction"""
    amount: float = Field(..., gt=0)
    category_id: Optional[int] = None
    description: str = Field(..., min_length=1, max_length=255)
    merchant: Optional[str] = None
    transaction_type: str = Field(..., pattern="^(income|expense)$")
    date: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 250.50,
                "category_id": 1,
                "description": "Grocery shopping",
                "merchant": "Walmart",
                "transaction_type": "expense",
                "date": "2026-06-07T10:30:00"
            }
        }


class TransactionResponse(BaseModel):
    """Schema for transaction response"""
    id: int
    user_id: int
    amount: float
    category_id: Optional[int]
    description: str
    merchant: Optional[str]
    extracted_merchant: Optional[str] = None
    transaction_type: str
    date: datetime
    category_confidence: Optional[float] = None
    categorization_method: Optional[str] = None
    review_status: Optional[str] = None
    friend_id: Optional[int] = None
    debt_type: Optional[str] = None
    debt_direction: Optional[str] = None
    is_friend_transaction: Optional[bool] = False
    is_needs_review: Optional[bool] = False
    review_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionCategoryCorrectionRequest(BaseModel):
    category_id: int


# ==================== Category Schemas ====================

class CategoryCreate(BaseModel):
    """Schema for creating a category"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class CategoryResponse(BaseModel):
    """Schema for category response"""
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


# ==================== Friends / Debt Schemas ====================

class FriendCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    phone: Optional[str] = None
    note: Optional[str] = None


class FriendUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    phone: Optional[str] = None
    note: Optional[str] = None
    is_archived: Optional[bool] = None


class FriendSummary(BaseModel):
    id: int
    user_id: int
    name: str
    normalized_name: str
    phone: Optional[str] = None
    note: Optional[str] = None
    is_archived: bool
    total_lent: float
    total_borrowed: float
    total_friend_paid_back: float
    total_i_paid_back: float
    net_balance: float
    status: str
    last_transaction_date: Optional[datetime] = None
    created_at: datetime


class FriendDashboardSummary(BaseModel):
    total_friends: int
    friends_owe_me: float
    i_owe_friends: float
    net_balance: float
    settled_friends: int
    unsettled_friends: int
    friends: List[FriendSummary]


class DebtCreate(BaseModel):
    amount: float = Field(..., gt=0)
    debt_type: str
    direction: str
    note: Optional[str] = None
    transaction_id: Optional[int] = None


class DebtResponse(BaseModel):
    id: int
    user_id: int
    friend_id: int
    transaction_id: Optional[int] = None
    amount: float
    debt_type: str
    direction: str
    status: str
    note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DebtUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    debt_type: Optional[str] = None
    direction: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


class LinkFriendRequest(BaseModel):
    friend_id: int
    debt_type: Optional[str] = None
    debt_direction: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    note: Optional[str] = None


class FriendPaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    debt_type: str
    direction: str
    note: Optional[str] = None


class SplitFriendShare(BaseModel):
    friend_id: int
    amount: float = Field(..., gt=0)
    note: Optional[str] = None


class SplitExpenseRequest(BaseModel):
    total_amount: float = Field(..., gt=0)
    transaction_id: Optional[int] = None
    description: Optional[str] = None
    equal_split: bool = False
    shares: List[SplitFriendShare]


class FriendSuggestionResponse(BaseModel):
    transaction_id: int
    description: str
    amount: float
    transaction_type: str
    friend_id: Optional[int]
    friend_name: Optional[str]
    confidence: float
    reason: str


class FriendDetailResponse(BaseModel):
    friend: FriendSummary
    transactions: List[TransactionResponse]


# ==================== Budget Schemas ====================

class BudgetCreate(BaseModel):
    """Schema for creating a budget"""
    category_id: int
    monthly_limit: float = Field(..., gt=0)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)


class BudgetUpdate(BaseModel):
    category_id: int
    monthly_limit: float = Field(..., gt=0)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    is_active: bool = True


class BudgetResponse(BaseModel):
    """Schema for budget response"""
    id: int
    user_id: int
    category_id: int
    category_name: Optional[str] = None
    monthly_limit: float
    month: int
    year: int
    alert_threshold: float
    smart_milestones: List[int] = []
    reached_milestones: List[int] = []
    next_milestone: Optional[int] = None
    actual_spent: float
    remaining_amount: float
    percentage_used: float
    status: str
    alert_message: Optional[str] = None
    created_at: datetime
    is_active: bool


# ==================== Savings Goal Schemas ====================

class SavingsGoalCreate(BaseModel):
    """Schema for creating a savings goal"""
    name: str = Field(..., min_length=1, max_length=100)
    target_amount: float = Field(..., gt=0)
    current_amount: float = Field(default=0, ge=0)
    monthly_contribution: float = Field(default=0, ge=0)
    target_date: datetime


class SavingsGoalUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    target_amount: float = Field(..., gt=0)
    current_amount: float = Field(default=0, ge=0)
    monthly_contribution: float = Field(default=0, ge=0)
    target_date: datetime
    status: str = "active"


class SavingsGoalResponse(BaseModel):
    """Schema for savings goal response"""
    id: int
    user_id: int
    name: str
    target_amount: float
    current_amount: float
    monthly_contribution: float
    remaining_amount: float
    progress_percentage: float
    months_required: Optional[int] = None
    estimated_completion_date: Optional[datetime] = None
    ai_suggestion: str
    target_date: datetime
    created_at: datetime
    status: str


# ==================== Investment Schemas ====================

class AccountBalanceCreate(BaseModel):
    account_name: str = Field(default="Current balance", min_length=1, max_length=120)
    balance_amount: float = Field(..., ge=0)


class AccountBalanceResponse(BaseModel):
    id: int
    user_id: int
    account_name: str
    balance_amount: float
    currency: str
    recorded_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvestmentHoldingCreate(BaseModel):
    asset_name: str = Field(..., min_length=1, max_length=150)
    symbol: str = Field(..., min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=30)
    quantity: float = Field(..., gt=0)
    average_buy_price: float = Field(..., gt=0)
    current_price: Optional[float] = Field(default=None, gt=0)


class InvestmentHoldingUpdate(InvestmentHoldingCreate):
    pass


class InvestmentHoldingResponse(BaseModel):
    id: int
    user_id: int
    asset_name: str
    symbol: str
    exchange: str
    quantity: float
    average_buy_price: float
    invested_amount: float
    current_price: Optional[float] = None
    current_value: float
    pnl_amount: float
    pnl_percent: float
    source: str
    last_price_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvestmentInsightResponse(BaseModel):
    title: str
    message: str
    severity: str


class InvestmentSummaryResponse(BaseModel):
    savings_goal_total: float
    savings_current_total: float
    account_balance: Optional[AccountBalanceResponse] = None
    manual_invested_amount: float
    auto_detected_invested_amount: float
    total_invested_amount: float
    current_portfolio_value: float
    total_pnl_amount: float
    total_pnl_percent: float
    net_worth: float
    holdings: List[InvestmentHoldingResponse]
    insights: List[InvestmentInsightResponse]


# ==================== Dashboard Schemas ====================

class DashboardMetric(BaseModel):
    label: str
    value: float


class CategoryBreakdownItem(BaseModel):
    category_id: Optional[int]
    category_name: str
    total: float


class DashboardSummary(BaseModel):
    month: int
    year: int
    total_income: float
    total_expenses: float
    total_savings: float
    investment_savings: float = 0
    remaining_balance_savings: float = 0
    effective_savings: float = 0
    savings_rate: float
    effective_savings_rate: float = 0
    monthly_savings_trend: float = 0
    transaction_count: int
    top_category: Optional[str]
    top_merchant: Optional[str] = None
    recurring_subscription_count: int = 0
    recurring_subscription_total: float = 0
    budget_health_score: int = 0
    category_breakdown: List[CategoryBreakdownItem]


class ChartDataPoint(BaseModel):
    name: str
    value: float


class IncomeExpenseChart(BaseModel):
    income: float
    expenses: float


class MonthlySpendingPoint(BaseModel):
    month: str
    expenses: float


class DashboardChartsResponse(BaseModel):
    month: int
    year: int
    category_breakdown: List[ChartDataPoint]
    income_vs_expense: IncomeExpenseChart
    monthly_spending: List[MonthlySpendingPoint]
    top_merchants: List[ChartDataPoint]


class BudgetUsageChartItem(BaseModel):
    category_id: int
    category_name: str
    limit: float
    spent: float
    remaining: float
    percentage_used: float
    status: str


class SuggestedBudgetResponse(BaseModel):
    id: Optional[int] = None
    category_id: int
    category_name: str
    period: str
    average_spend: float
    suggested_amount: float
    has_custom_budget: bool = False
    custom_budget_amount: Optional[float] = None


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


# ==================== AI Insight Schemas ====================

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


# ==================== AI Budget Recommendation Schemas ====================

class BudgetRecommendationResponse(BaseModel):
    id: str
    title: str
    recommendation_text: str
    category_name: Optional[str] = None
    priority: str
    potential_savings: float
    impact_score: float
    reason: str


class BudgetRecommendationsResponse(BaseModel):
    month: int
    year: int
    total_income: float
    total_expenses: float
    savings_rate: float
    recommendations: List[BudgetRecommendationResponse]


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


# ==================== Expense Forecast Schemas ====================

class ForecastCategoryPrediction(BaseModel):
    category_id: Optional[int] = None
    category_name: str
    predicted_amount: float


class ForecastHistoryPoint(BaseModel):
    month: str
    actual_expenses: float
    predicted_expenses: Optional[float] = None


class ExpenseForecastResponse(BaseModel):
    id: int
    forecast_month: str
    predicted_amount: float
    confidence_lower: float
    confidence_upper: float
    model_used: str
    accuracy: Optional[float] = None
    feature_summary: dict
    category_forecasts: List[ForecastCategoryPrediction]
    history: List[ForecastHistoryPoint]
    created_at: datetime


# ==================== Subscription Schemas ====================

class SubscriptionTransactionItem(BaseModel):
    id: int
    description: str
    merchant: Optional[str] = None
    amount: float
    date: datetime

    class Config:
        from_attributes = True


class SubscriptionItem(BaseModel):
    merchant_name: str
    monthly_amount: float
    transaction_count: int
    first_seen: datetime
    last_seen: datetime
    next_expected_date: datetime
    confidence: float
    is_active: bool
    review_suggestion: Optional[str] = None
    transactions: List[SubscriptionTransactionItem]


class SubscriptionChartItem(BaseModel):
    name: str
    value: float


class SubscriptionsResponse(BaseModel):
    active_subscriptions: List[SubscriptionItem]
    monthly_total: float
    subscription_count: int
    marked_transaction_ids: List[int]
    chart_data: List[SubscriptionChartItem]


# ==================== AI Financial Assistant Schemas ====================

class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class AssistantPendingAction(BaseModel):
    audit_id: int
    action_type: str
    explanation: str
    preview: dict
    requires_confirmation: bool = True


class AssistantChatResponse(BaseModel):
    message: str
    intent: str
    read_only: bool
    data: Optional[dict] = None
    pending_action: Optional[AssistantPendingAction] = None
    suggested_questions: List[str] = []


class AssistantConfirmRequest(BaseModel):
    audit_id: int
    confirm: bool = True


class AssistantConfirmResponse(BaseModel):
    message: str
    audit_id: int
    status: str
    result: Optional[dict] = None


class AssistantHistoryResponse(BaseModel):
    id: int
    user_id: int
    user_message: str
    assistant_response: str
    intent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== General Response Schemas ====================

class MessageResponse(BaseModel):
    """Schema for simple message response"""
    message: str


class ErrorResponse(BaseModel):
    """Schema for error response"""
    detail: str
    status_code: int

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid credentials",
                "status_code": 401
            }
        }
