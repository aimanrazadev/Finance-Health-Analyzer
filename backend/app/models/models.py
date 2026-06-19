"""SQLAlchemy ORM models for the focused Finance Health Analyzer."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    """Registered account used by auth and per-user data isolation."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class Transaction(Base):
    """Clean transaction ledger used by categorization, analytics, and AI advice."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, nullable=True, index=True)
    merchant_id = Column(Integer, nullable=True, index=True)
    uploaded_file_id = Column(Integer, nullable=True, index=True)
    description = Column(String(255), nullable=False)
    merchant = Column(String(150), nullable=True)
    extracted_merchant = Column(String(150), nullable=True)
    reference_no = Column(String(150), nullable=True)
    withdrawal_amount = Column(Float, nullable=True)
    deposit_amount = Column(Float, nullable=True)
    balance = Column(Float, nullable=True)
    transaction_type = Column(String(50), nullable=False)
    date = Column(DateTime, nullable=False)
    payment_method = Column(String(100), nullable=True)
    source = Column(String(50), default="manual")
    friend_id = Column(Integer, nullable=True, index=True)
    is_friend_transaction = Column(Boolean, default=False)
    category_confidence = Column(Float, default=0.30)
    categorization_method = Column(String(50), default="needs_review")
    is_needs_review = Column(Boolean, default=False)
    review_status = Column(String(50), default="approved")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Category(Base):
    """Transaction category catalog used across badges, charts, and ML labels."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)
    icon = Column(String(50), nullable=True)


class ImportProfile(Base):
    """Remembered bank statement column mappings for repeat uploads."""
    __tablename__ = "import_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    profile_name = Column(String(150), nullable=False)
    bank_name = Column(String(150), nullable=True, index=True)
    file_type = Column(String(50), nullable=True)
    header_signature = Column(String(500), nullable=False, index=True)
    column_mapping = Column(Text, nullable=False)
    preferences = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Merchant(Base):
    """Canonical merchant directory built from extracted transaction merchants."""
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    canonical_name = Column(String(150), nullable=False)
    normalized_name = Column(String(150), nullable=False, index=True)
    aliases = Column(Text, nullable=True)
    transaction_count = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AiInsight(Base):
    """Stored AI-generated financial advice for a user."""
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    insight_text = Column(Text, nullable=False)
    insight_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_read = Column(Boolean, default=False)


class AdvisorChat(Base):
    """One AI Financial Advisor conversation for a user."""
    __tablename__ = "advisor_chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(180), nullable=False, default="New advisor chat")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AdvisorMessage(Base):
    """Stored user or assistant message inside an advisor chat."""
    __tablename__ = "advisor_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, nullable=False, index=True)
    role = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AdvisorRecommendation(Base):
    """Actionable AI suggestion extracted from an advisor response."""
    __tablename__ = "advisor_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(Integer, nullable=False, index=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    estimated_savings = Column(Float, default=0)
    category = Column(String(100), nullable=True)
    status = Column(String(30), default="pending")
    created_at = Column(DateTime, server_default=func.now())


class FinancialScore(Base):
    """Financial health score snapshots generated from transaction analytics."""
    __tablename__ = "financial_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    overall_score = Column(Integer, nullable=False)
    savings_score = Column(Integer, nullable=False)
    budget_score = Column(Integer, nullable=False)
    stability_score = Column(Integer, nullable=False)
    subscription_score = Column(Integer, default=60)
    debt_score = Column(Integer, nullable=False)
    emergency_fund_score = Column(Integer, nullable=False)
    calculated_at = Column(DateTime, server_default=func.now())


class Subscription(Base):
    """Detected recurring subscription from categorized transaction history."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    merchant_name = Column(String(150), nullable=False)
    category_id = Column(Integer, nullable=True, index=True)
    amount = Column(Float, nullable=False, default=0)
    billing_period = Column(String(50), default="monthly")
    next_expected_payment = Column(DateTime, nullable=True)
    confidence = Column(Float, default=0.75)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UploadedFile(Base):
    """Bank statement upload audit record."""
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


class UserLearning(Base):
    """Legacy merchant-category learning record used by categorization fallback."""
    __tablename__ = "user_learning"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    merchant = Column(String(150), nullable=False)
    category_id = Column(Integer, nullable=False)
    frequency = Column(Integer, default=1)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CategoryCorrection(Base):
    """History of user corrections used as labeled ML training data."""
    __tablename__ = "category_corrections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=False, index=True)
    old_category_id = Column(Integer, nullable=True)
    new_category_id = Column(Integer, nullable=False)
    merchant = Column(String(150), nullable=True)
    extracted_merchant = Column(String(150), nullable=True)
    original_description = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    old_confidence = Column(Float, nullable=True)
    old_method = Column(String(50), nullable=True)
    correction_source = Column(String(50), default="manual")
    created_at = Column(DateTime, server_default=func.now())


class CategoryLearningRule(Base):
    """User-specific merchant rules learned from manual category corrections."""
    __tablename__ = "category_learning_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    merchant_pattern = Column(String(150), nullable=False)
    merchant_name = Column(String(150), nullable=True)
    normalized_merchant = Column(String(150), nullable=False, index=True)
    category_id = Column(Integer, nullable=False)
    confidence_score = Column(Float, default=0.95)
    confidence = Column(Float, default=1.0)
    times_used = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Friend(Base):
    """Saved person/contact used to group friend-related transactions."""
    __tablename__ = "friends"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_friends_user_normalized_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    normalized_name = Column(String(150), nullable=False, index=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FriendTransactionLink(Base):
    """Stable link between a friend and a matched bank transaction."""
    __tablename__ = "friend_transaction_links"
    __table_args__ = (
        UniqueConstraint("user_id", "transaction_id", name="uq_friend_links_user_transaction"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    friend_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=True)
    transaction_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class FriendMerchantLearning(Base):
    """Merchant/person text learned from transactions linked to a friend."""
    __tablename__ = "friend_merchant_learning"
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", "normalized_merchant", name="uq_friend_learning_user_friend_merchant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    friend_id = Column(Integer, nullable=False, index=True)
    merchant_pattern = Column(String(150), nullable=False)
    normalized_merchant = Column(String(150), nullable=False, index=True)
    confidence = Column(Float, default=0.95)
    usage_count = Column(Integer, default=1)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
