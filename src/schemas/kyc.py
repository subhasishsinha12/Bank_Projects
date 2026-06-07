from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.models.kyc import DocumentType, VerificationStatus, KYCType


class KYCDocumentCreate(BaseModel):
    customer_id: str
    document_type: DocumentType
    document_number: Optional[str] = None
    document_expiry: Optional[str] = None
    kyc_type: KYCType = KYCType.FRESH


class KYCDocumentResponse(BaseModel):
    id: str
    customer_id: str
    kyc_type: KYCType
    document_type: DocumentType
    document_number: Optional[str] = None
    document_expiry: Optional[str] = None
    file_name: Optional[str] = None
    verification_status: VerificationStatus
    verification_method: Optional[str] = None
    ocr_confidence: Optional[float] = None
    extracted_data: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AadhaarOTPRequest(BaseModel):
    customer_id: str
    aadhaar_number: str


class AadhaarOTPVerify(BaseModel):
    customer_id: str
    aadhaar_number: str
    otp: str
    transaction_id: str


class PANVerifyRequest(BaseModel):
    customer_id: str
    pan_number: str
    full_name: str
    date_of_birth: str


class ReKYCInitiateRequest(BaseModel):
    customer_id: str
    trigger_reason: str = "periodic"
    preferred_channel: Optional[str] = "email"


class ReKYCRequestResponse(BaseModel):
    id: str
    customer_id: str
    status: str
    trigger_reason: str
    due_date: Optional[datetime] = None
    initiated_at: Optional[datetime] = None
    reminder_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CKYCSearchRequest(BaseModel):
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    mobile: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None


class CKYCUpdateRequest(BaseModel):
    customer_id: str
    updated_fields: Dict[str, Any]
    supporting_documents: Optional[List[str]] = None


class CKYCResponse(BaseModel):
    ckyc_id: Optional[str] = None
    found: bool
    customer_data: Optional[Dict[str, Any]] = None
    kyc_status: Optional[str] = None
    last_updated: Optional[str] = None
    institution: Optional[str] = None


class KYCStatusResponse(BaseModel):
    customer_id: str
    overall_status: str
    kyc_completed: bool
    ckyc_verified: bool
    documents_submitted: int
    documents_verified: int
    pending_documents: List[str]
    kyc_expiry_date: Optional[datetime] = None
    rekyc_due_date: Optional[datetime] = None
    is_rekyc_overdue: bool = False
