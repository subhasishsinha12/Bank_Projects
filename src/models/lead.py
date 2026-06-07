from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from src.database import Base


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    CONVERTED = "converted"
    LOST = "lost"
    NURTURING = "nurturing"


class LeadSource(str, enum.Enum):
    WEBSITE = "website"
    MOBILE_APP = "mobile_app"
    BRANCH_WALK_IN = "branch_walk_in"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    DIGITAL_CAMPAIGN = "digital_campaign"
    TELE_CALLING = "tele_calling"
    DSA = "dsa"
    PARTNER = "partner"


class LeadQuality(str, enum.Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, unique=True, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)

    # Basic Info (before customer creation)
    name = Column(String(200))
    email = Column(String(255), index=True)
    mobile = Column(String(20), index=True)
    city = Column(String(100))
    state = Column(String(100))

    # Lead Details
    source = Column(SAEnum(LeadSource), default=LeadSource.WEBSITE)
    status = Column(SAEnum(LeadStatus), default=LeadStatus.NEW)
    quality = Column(SAEnum(LeadQuality), default=LeadQuality.COLD)

    # Product Interest
    interested_product = Column(String(100))
    interested_amount = Column(Float)

    # Scoring
    lead_score = Column(Integer, default=0)
    score_breakdown = Column(Text)  # JSON with scoring components

    # Engagement
    engagement_count = Column(Integer, default=0)
    last_contact_date = Column(DateTime)
    next_follow_up_date = Column(DateTime)
    assigned_to = Column(String(100))

    # AI-driven personalisation fields
    persona_tags = Column(Text)  # JSON array: ["young_professional", "first_time_borrower"]
    recommended_products = Column(Text)  # JSON array
    personalised_message = Column(Text)
    communication_preference = Column(String(50))

    # Conversion
    converted_at = Column(DateTime)
    conversion_value = Column(Float)
    loss_reason = Column(Text)

    # UTM / Campaign Tracking
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="leads")
    activities = relationship("LeadActivity", back_populates="lead")


class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)

    activity_type = Column(String(50))  # email_sent, call_made, sms_sent, page_view, etc.
    activity_description = Column(Text)
    channel = Column(String(50))
    outcome = Column(String(100))
    score_impact = Column(Integer, default=0)

    performed_by = Column(String(100))
    performed_at = Column(DateTime, server_default=func.now())

    lead = relationship("Lead", back_populates="activities")
