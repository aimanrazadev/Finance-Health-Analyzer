"""
SQLAlchemy ORM models for the application
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """User model - stores user account information"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class Transaction(Base):
    """Transaction model - stores financial transactions"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, nullable=True, index=True)
    uploaded_file_id = Column(Integer, nullable=True, index=True)
    description = Column(String(255), nullable=False)
    merchant = Column(String(150), nullable=True)
    reference_no = Column(String(150), nullable=True)
    withdrawal_amount = Column(Float, nullable=True)
    deposit_amount = Column(Float, nullable=True)
    balance = Column(Float, nullable=True)
    transaction_type = Column(String(50), nullable=False)  # 'income', 'expense'
    date = Column(DateTime, nullable=False)
    payment_method = Column(String(100), nullable=True)
    source = Column(String(50), default="manual")
    is_recurring = Column(Boolean, default=False)
    category_confidence = Column(Float, default=0.30)
    categorization_method = Column(String(50), default="needs_review")
    friend_id = Column(Integer, nullable=True, index=True)
    debt_type = Column(String(50), nullable=True)
    debt_direction = Column(String(50), nullable=True)
    is_friend_transaction = Column(Boolean, default=False)
    is_needs_review = Column(Boolean, default=False)
    review_reason = Column(String(255), nullable=True)
    original_category_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount})>"


class Category(Base):
    """Category model - expense categories"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # hex color
    icon = Column(String(50), nullable=True)  # icon name

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class Budget(Base):
    """Budget model - user-defined spending budgets"""
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    category_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    period = Column(String(50), nullable=False)  # 'monthly', 'yearly'
    alert_threshold = Column(Float, default=80.0)  # percentage
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Budget(id={self.id}, user_id={self.user_id})>"


class SavingsGoal(Base):
    """Savings Goal model - user saving targets"""
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    monthly_contribution = Column(Float, default=0.0)
    target_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    status = Column(String(50), default="active")  # 'active', 'completed', 'paused'

    def __repr__(self):
        return f"<SavingsGoal(id={self.id}, user_id={self.user_id}, name={self.name})>"


class AiInsight(Base):
    """AI Insights model - AI-generated spending insights"""
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    insight_text = Column(Text, nullable=False)
    insight_type = Column(String(50), nullable=False)  # 'spending', 'savings', 'budget', etc.
    created_at = Column(DateTime, server_default=func.now())
    is_read = Column(Boolean, default=False)

    def __repr__(self):
        return f"<AiInsight(id={self.id}, user_id={self.user_id})>"


class ForecastResult(Base):
    """Forecast model - ML-based expense forecasts"""
    __tablename__ = "forecast_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    category_id = Column(Integer, nullable=True)
    forecast_month = Column(String(50), nullable=False)  # 'YYYY-MM'
    predicted_amount = Column(Float, nullable=False)
    confidence_lower = Column(Float, nullable=False)
    confidence_upper = Column(Float, nullable=False)
    model_used = Column(String(50), nullable=False)  # 'linear', 'random_forest', etc.
    accuracy = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ForecastResult(id={self.id}, category_id={self.category_id})>"


class FinancialScore(Base):
    """Financial Health Score model"""
    __tablename__ = "financial_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    overall_score = Column(Integer, nullable=False)  # 0-100
    savings_score = Column(Integer, nullable=False)
    budget_score = Column(Integer, nullable=False)
    stability_score = Column(Integer, nullable=False)
    debt_score = Column(Integer, nullable=False)
    emergency_fund_score = Column(Integer, nullable=False)
    calculated_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<FinancialScore(id={self.id}, user_id={self.user_id}, score={self.overall_score})>"


class ChatHistory(Base):
    """Chat History model - AI chatbot conversations"""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ChatHistory(id={self.id}, user_id={self.user_id})>"


class UploadedFile(Base):
    """Uploaded Files model - tracks bank statement uploads"""
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=False)
    transaction_count = Column(Integer, default=0)
    upload_status = Column(String(50), default="processed")
    total_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    upload_date = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<UploadedFile(id={self.id}, user_id={self.user_id}, filename={self.filename})>"


class UserLearning(Base):
    """User Learning model - stores merchant-category associations learned from user corrections"""
    __tablename__ = "user_learning"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    merchant = Column(String(150), nullable=False)
    category_id = Column(Integer, nullable=False)
    frequency = Column(Integer, default=1)  # how many times user confirmed this
    confidence = Column(Float, nullable=True)  # AI confidence when category was suggested
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserLearning(id={self.id}, merchant={self.merchant})>"


class CategoryCorrection(Base):
    """Category correction history - stores user overrides for transaction categories"""
    __tablename__ = "category_corrections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=False, index=True)
    old_category_id = Column(Integer, nullable=True)
    new_category_id = Column(Integer, nullable=False)
    merchant = Column(String(150), nullable=True)
    original_description = Column(Text, nullable=True)
    correction_source = Column(String(50), default="manual")
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<CategoryCorrection(id={self.id}, transaction_id={self.transaction_id})>"


class CategoryLearningRule(Base):
    """User-specific merchant rules learned from manual category corrections."""
    __tablename__ = "category_learning_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    merchant_pattern = Column(String(150), nullable=False)
    normalized_merchant = Column(String(150), nullable=False, index=True)
    category_id = Column(Integer, nullable=False)
    confidence_score = Column(Float, default=0.95)
    times_used = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CategoryLearningRule(id={self.id}, merchant={self.normalized_merchant})>"


class Friend(Base):
    """Friend/person tracked for lending, borrowing, and repayment balances."""
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    normalized_name = Column(String(150), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Debt(Base):
    """Debt ledger entry attached to a friend and optionally a bank transaction."""
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    friend_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=True, index=True)
    amount = Column(Float, nullable=False)
    debt_type = Column(String(50), nullable=False)
    direction = Column(String(50), nullable=False)
    status = Column(String(50), default="unpaid")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FriendSettlement(Base):
    """Audit record for settlement actions that zero or adjust a friend's balance."""
    __tablename__ = "friend_settlements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    friend_id = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    settlement_type = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class FriendTransactionLink(Base):
    """Join/audit table linking bank transactions to friend debt records."""
    __tablename__ = "friend_transaction_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    friend_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=False, index=True)
    debt_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())


class FriendMerchantLearning(Base):
    """User-specific mapping from transaction narration patterns to friends."""
    __tablename__ = "friend_merchant_learning"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    friend_id = Column(Integer, nullable=False, index=True)
    raw_transaction_text = Column(Text, nullable=False)
    normalized_text = Column(String(255), nullable=False, index=True)
    confidence = Column(Float, default=0.95)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RecurringTransaction(Base):
    """Recurring Transactions model - for recurring bills/income"""
    __tablename__ = "recurring_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, nullable=True)
    recurrence = Column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly'
    next_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<RecurringTransaction(id={self.id}, user_id={self.user_id})>"
