from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from src.database import Base


class OnboardingStage(str, enum.Enum):
    WELCOME = "welcome"
    PROFILE_COLLECTION = "profile_collection"
    PRODUCT_SELECTION = "product_selection"
    KYC_INITIATION = "kyc_initiation"
    DOCUMENT_UPLOAD = "document_upload"
    VERIFICATION = "verification"
    ACCOUNT_SETUP = "account_setup"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_token = Column(String(100), unique=True, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)

    # Session State
    current_stage = Column(SAEnum(OnboardingStage), default=OnboardingStage.WELCOME)
    is_active = Column(Boolean, default=True)
    language = Column(String(10), default="en")

    # Progress Tracking
    stages_completed = Column(Text, default="[]")  # JSON array
    collected_data = Column(Text, default="{}")    # JSON of collected info
    product_selected = Column(String(100))

    # Personalization
    persona = Column(String(100))  # young_professional, homemaker, senior_citizen, etc.
    intent_signals = Column(Text)  # JSON array of detected intents

    # Timing
    started_at = Column(DateTime, server_default=func.now())
    last_active_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    time_to_complete_minutes = Column(Integer)

    # Referral / Channel
    channel = Column(String(50))  # web, mobile, whatsapp, ivr
    device_type = Column(String(50))

    customer = relationship("Customer", back_populates="onboarding_sessions")
    messages = relationship("OnboardingMessage", back_populates="session", order_by="OnboardingMessage.created_at")


class OnboardingMessage(Base):
    __tablename__ = "onboarding_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("onboarding_sessions.id"), nullable=False)

    role = Column(SAEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # Metadata
    intent_detected = Column(String(100))
    entities_extracted = Column(Text)  # JSON
    stage_at_message = Column(String(50))

    # For assistant messages
    suggestion_type = Column(String(50))  # text, options, document_upload, otp
    options_provided = Column(Text)       # JSON array if choices offered

    created_at = Column(DateTime, server_default=func.now())

    session = relationship("OnboardingSession", back_populates="messages")
