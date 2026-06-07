"""
DPDP Consent Models
Digital Personal Data Protection Act 2023 — RBI Compliance
Stores every consent artefact, processing record, subject request, and breach event.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from src.database import Base


class ConsentPurpose(str, enum.Enum):
    KYC_VERIFICATION        = "kyc_verification"
    CREDIT_ASSESSMENT       = "credit_assessment"
    PRODUCT_PERSONALISATION = "product_personalisation"
    MARKETING_COMMUNICATION = "marketing_communication"
    ANALYTICS               = "analytics"
    FRAUD_PREVENTION        = "fraud_prevention"
    REGULATORY_REPORTING    = "regulatory_reporting"
    ACCOUNT_AGGREGATOR      = "account_aggregator"
    THIRD_PARTY_SHARING     = "third_party_sharing"


class ConsentStatus(str, enum.Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    REVOKED   = "revoked"
    EXPIRED   = "expired"
    PAUSED    = "paused"


class DataCategory(str, enum.Enum):
    PERSONAL_IDENTITY   = "personal_identity"       # name, DOB, gender
    CONTACT_INFO        = "contact_info"             # mobile, email, address
    FINANCIAL_DATA      = "financial_data"           # income, transactions
    IDENTITY_DOCUMENTS  = "identity_documents"       # PAN, Aadhaar scans
    BIOMETRIC           = "biometric"                # photo, fingerprint
    BEHAVIOURAL         = "behavioural"              # app usage, click patterns
    CREDIT_HISTORY      = "credit_history"           # bureau data
    DEVICE_DATA         = "device_data"              # IP, device ID


class LegalBasis(str, enum.Enum):
    CONSENT           = "consent"
    LEGAL_OBLIGATION  = "legal_obligation"     # RBI / KYC mandate
    LEGITIMATE_INTEREST = "legitimate_interest"
    VITAL_INTEREST    = "vital_interest"
    CONTRACT          = "contract"


class DSRType(str, enum.Enum):  # Data Subject Request types
    ACCESS       = "access"       # Right to access data
    CORRECTION   = "correction"   # Right to correct data
    ERASURE      = "erasure"      # Right to be forgotten
    PORTABILITY  = "portability"  # Right to data portability
    WITHDRAWAL   = "withdrawal"   # Consent withdrawal
    GRIEVANCE    = "grievance"    # Complaint / grievance


class ConsentRecord(Base):
    """
    Central consent artefact per DPDP Act §6.
    One record per customer × purpose × data-category combination.
    """
    __tablename__ = "consent_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    consent_id = Column(String, unique=True, index=True,
                        default=lambda: f"CONSENT-{str(uuid.uuid4())[:8].upper()}")

    customer_id  = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    purpose      = Column(SAEnum(ConsentPurpose), nullable=False)
    legal_basis  = Column(SAEnum(LegalBasis), default=LegalBasis.CONSENT)
    status       = Column(SAEnum(ConsentStatus), default=ConsentStatus.PENDING)

    # What data is covered
    data_categories = Column(Text, nullable=False)   # JSON list of DataCategory values
    data_processors = Column(Text)                   # JSON list of third parties if any

    # Consent text / version shown to user
    consent_version  = Column(String(20), nullable=False)
    consent_text_key = Column(String(100))           # key into consent-text registry
    language         = Column(String(10), default="en")

    # Lifecycle
    given_at    = Column(DateTime)
    expires_at  = Column(DateTime)
    revoked_at  = Column(DateTime)
    paused_at   = Column(DateTime)
    last_renewed_at = Column(DateTime)

    # Collection metadata
    collection_channel = Column(String(50))    # web, mobile, branch, ivr
    collection_ip      = Column(String(45))
    user_agent         = Column(String(500))

    # Signed artefact (base64-encoded JWS for audit)
    signed_artefact = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer    = relationship("Customer", back_populates="consents")
    audit_trail = relationship("ConsentAuditLog", back_populates="consent",
                               order_by="ConsentAuditLog.created_at")
    processing_records = relationship("DataProcessingRecord", back_populates="consent")


class ConsentAuditLog(Base):
    """Immutable audit log of every state change on a consent record."""
    __tablename__ = "consent_audit_logs"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    consent_id  = Column(String, ForeignKey("consent_records.id"), nullable=False)
    event_type  = Column(String(50), nullable=False)   # created, activated, revoked, renewed, expired
    previous_status = Column(String(30))
    new_status      = Column(String(30))
    actor           = Column(String(100))              # customer | system | officer
    reason          = Column(Text)
    ip_address      = Column(String(45))
    created_at      = Column(DateTime, server_default=func.now())

    consent = relationship("ConsentRecord", back_populates="audit_trail")


class DataProcessingRecord(Base):
    """
    Record of every time personal data is accessed / processed.
    Required by DPDP Act §11 (Processing) and RBI audit trail mandate.
    """
    __tablename__ = "data_processing_records"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    consent_id  = Column(String, ForeignKey("consent_records.id"), nullable=True)
    customer_id = Column(String, nullable=False, index=True)

    operation       = Column(String(50), nullable=False)  # read, write, share, delete
    data_categories = Column(Text)                        # JSON: which categories accessed
    api_endpoint    = Column(String(200))                 # which endpoint triggered this
    processed_by    = Column(String(100))                 # service/user that accessed
    legal_basis     = Column(String(50))
    third_party     = Column(String(200))                 # if shared externally

    created_at = Column(DateTime, server_default=func.now())

    consent = relationship("ConsentRecord", back_populates="processing_records")


class DataSubjectRequest(Base):
    """
    DPDP §12-17: Handles access, correction, erasure, portability,
    nomination, and grievance requests from data principals.
    """
    __tablename__ = "data_subject_requests"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dsr_id       = Column(String, unique=True, index=True,
                          default=lambda: f"DSR-{str(uuid.uuid4())[:8].upper()}")
    customer_id  = Column(String, ForeignKey("customers.id"), nullable=False)
    request_type = Column(SAEnum(DSRType), nullable=False)
    status       = Column(String(30), default="received")   # received, in_progress, completed, rejected
    description  = Column(Text)

    # Resolution
    resolved_at    = Column(DateTime)
    resolved_by    = Column(String(100))
    resolution_note = Column(Text)

    # Escalation (DPDP: resolve within 30 days or escalate to DPCI)
    due_date       = Column(DateTime)
    escalated_at   = Column(DateTime)
    escalation_ref = Column(String(100))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", back_populates="dsr_requests")


class DataBreachRecord(Base):
    """
    DPDP §8(6): Notify DPCI within 72 hours of discovering a breach.
    """
    __tablename__ = "data_breach_records"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    breach_ref    = Column(String(50), unique=True, index=True,
                           default=lambda: f"BREACH-{str(uuid.uuid4())[:8].upper()}")

    discovered_at    = Column(DateTime, nullable=False)
    notification_due = Column(DateTime)           # discovered_at + 72h
    dpci_notified_at = Column(DateTime)
    customers_notified_at = Column(DateTime)

    breach_type      = Column(String(100))        # unauthorized_access, data_leak, ransomware
    data_categories_affected = Column(Text)       # JSON list
    estimated_records_affected = Column(Integer)
    description      = Column(Text)
    root_cause       = Column(Text)
    remediation_steps = Column(Text)
    status           = Column(String(30), default="open")   # open, notified, closed

    reported_by  = Column(String(100))
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())
