from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from src.database import Base


class CustomerSegment(str, enum.Enum):
    MASS = "mass"
    MASS_AFFLUENT = "mass_affluent"
    AFFLUENT = "affluent"
    HNI = "hni"
    UHNI = "uhni"


class CustomerStatus(str, enum.Enum):
    PROSPECT = "prospect"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    DORMANT = "dormant"
    CHURNED = "churned"


class RiskCategory(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, unique=True, index=True)

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(String(20))
    gender = Column(String(20))
    nationality = Column(String(100), default="Indian")

    # Contact
    email = Column(String(255), unique=True, index=True)
    mobile = Column(String(20), unique=True, index=True)
    alternate_mobile = Column(String(20))

    # Address
    address_line1 = Column(Text)
    address_line2 = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    country = Column(String(100), default="India")

    # Identity
    pan_number = Column(String(10), unique=True, index=True)
    aadhaar_number = Column(String(12))
    ckyc_id = Column(String(14), unique=True, index=True)  # 14-digit CKYC identifier

    # Financial Profile
    annual_income = Column(Float)
    employment_type = Column(String(50))
    employer_name = Column(String(200))
    credit_score = Column(Integer)
    existing_bank_accounts = Column(Integer, default=0)

    # Segmentation & Risk
    segment = Column(SAEnum(CustomerSegment), default=CustomerSegment.MASS)
    risk_category = Column(SAEnum(RiskCategory), default=RiskCategory.LOW)
    status = Column(SAEnum(CustomerStatus), default=CustomerStatus.PROSPECT)

    # KYC Status
    kyc_completed = Column(Boolean, default=False)
    kyc_completion_date = Column(DateTime)
    kyc_expiry_date = Column(DateTime)
    ckyc_verified = Column(Boolean, default=False)
    rekyc_due_date = Column(DateTime)

    # Personalization
    preferred_language = Column(String(20), default="en")
    preferred_channel = Column(String(50))
    product_interests = Column(Text)  # JSON array
    engagement_score = Column(Float, default=0.0)
    last_engagement_date = Column(DateTime)

    # Metadata
    source = Column(String(100))
    referral_code = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # AA-linked financial data
    aa_verified_income    = Column(Float)
    aa_verified_at        = Column(DateTime)
    aa_pre_approved_limit = Column(Float)

    # Relationships
    leads = relationship("Lead", back_populates="customer")
    kyc_documents = relationship("KYCDocument", back_populates="customer")
    onboarding_sessions = relationship("OnboardingSession", back_populates="customer")
    consents = relationship("ConsentRecord", back_populates="customer")
    dsr_requests = relationship("DataSubjectRequest", back_populates="customer")
    aa_consents = relationship("AAConsentArtefact", back_populates="customer")
    financial_summary = relationship("FinancialSummary", back_populates="customer",
                                     uselist=False)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
