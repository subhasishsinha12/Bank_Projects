from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from src.database import Base


class DocumentType(str, enum.Enum):
    # Identity Proof
    AADHAAR = "aadhaar"
    PAN = "pan"
    PASSPORT = "passport"
    VOTER_ID = "voter_id"
    DRIVING_LICENSE = "driving_license"
    # Address Proof
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    RENT_AGREEMENT = "rent_agreement"
    # Income Proof
    SALARY_SLIP = "salary_slip"
    ITR = "itr"
    FORM_16 = "form_16"
    BANK_STATEMENT_6M = "bank_statement_6m"
    # Photo
    PHOTOGRAPH = "photograph"
    # Business
    GST_CERTIFICATE = "gst_certificate"
    COI = "certificate_of_incorporation"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class KYCType(str, enum.Enum):
    FRESH = "fresh"
    REKYC = "rekyc"
    CKYC_FETCH = "ckyc_fetch"
    CKYC_UPDATE = "ckyc_update"
    VIDEO_KYC = "video_kyc"


class KYCDocument(Base):
    __tablename__ = "kyc_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    kyc_type = Column(SAEnum(KYCType), default=KYCType.FRESH)

    # Document Details
    document_type = Column(SAEnum(DocumentType), nullable=False)
    document_number = Column(String(100))
    document_expiry = Column(String(20))

    # File Storage
    file_path = Column(String(500))
    file_name = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))

    # OCR & Extracted Data
    extracted_data = Column(Text)  # JSON of OCR-extracted fields
    ocr_confidence = Column(Float)

    # Verification
    verification_status = Column(SAEnum(VerificationStatus), default=VerificationStatus.PENDING)
    verification_method = Column(String(50))  # ocr, manual, api, aadhaar_otp
    verified_at = Column(DateTime)
    verified_by = Column(String(100))
    rejection_reason = Column(Text)

    # CKYC Linkage
    ckyc_document_id = Column(String(100))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", back_populates="kyc_documents")
    verifications = relationship("KYCVerification", back_populates="document")


class KYCVerification(Base):
    __tablename__ = "kyc_verifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("kyc_documents.id"), nullable=True)
    customer_id = Column(String, nullable=False)

    # Verification Run
    verification_type = Column(String(50))  # aadhaar_otp, pan_nsdl, face_match, etc.
    request_payload = Column(Text)  # JSON
    response_payload = Column(Text)  # JSON
    is_successful = Column(Boolean, default=False)
    confidence_score = Column(Float)
    error_message = Column(Text)

    # Audit
    initiated_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("KYCDocument", back_populates="verifications")


class ReKYCRequest(Base):
    __tablename__ = "rekyc_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)

    # Status
    status = Column(String(50), default="pending")  # pending, initiated, completed, overdue
    trigger_reason = Column(String(100))  # periodic, risk_change, address_change, etc.

    # Dates
    due_date = Column(DateTime)
    initiated_at = Column(DateTime)
    completed_at = Column(DateTime)
    reminder_sent_at = Column(DateTime)

    # Communication
    reminder_channel = Column(String(50))
    reminder_count = Column(Integer, default=0)

    # Previous KYC Reference
    previous_kyc_date = Column(DateTime)
    changes_detected = Column(Text)  # JSON of changed fields

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
