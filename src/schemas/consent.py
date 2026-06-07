from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.models.consent import ConsentPurpose, ConsentStatus, DataCategory, LegalBasis, DSRType


class ConsentRequestCreate(BaseModel):
    customer_id: str
    purpose: ConsentPurpose
    data_categories: List[DataCategory]
    legal_basis: LegalBasis = LegalBasis.CONSENT
    language: str = "en"
    channel: str = "web"
    expiry_days: Optional[int] = None
    data_processors: Optional[List[str]] = None


class ConsentActivate(BaseModel):
    consent_id: str
    actor: str = "customer"


class ConsentRevoke(BaseModel):
    consent_id: str
    reason: Optional[str] = None


class ConsentResponse(BaseModel):
    id: str
    consent_id: str
    customer_id: str
    purpose: ConsentPurpose
    status: ConsentStatus
    legal_basis: LegalBasis
    data_categories: str
    consent_version: str
    language: str
    given_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    collection_channel: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConsentDashboardResponse(BaseModel):
    customer_id: str
    total_consents: int
    active: int
    revoked: int
    expired: int
    data_processing_events: int
    pending_dsr_requests: int
    consents: List[Dict[str, Any]]


class DSRCreate(BaseModel):
    customer_id: str
    request_type: DSRType
    description: Optional[str] = None


class DSRResponse(BaseModel):
    id: str
    dsr_id: str
    customer_id: str
    request_type: DSRType
    status: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BreachCreate(BaseModel):
    breach_type: str
    data_categories_affected: List[DataCategory]
    estimated_records_affected: int
    description: str
    discovered_at: Optional[datetime] = None
    reported_by: str = "security_team"


class BreachResponse(BaseModel):
    id: str
    breach_ref: str
    discovered_at: datetime
    notification_due: Optional[datetime] = None
    dpci_notified_at: Optional[datetime] = None
    breach_type: str
    estimated_records_affected: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ErasureResponse(BaseModel):
    customer_id: str
    pii_fields_anonymised: int
    consents_revoked: int
    message: str
    legal_retention_note: str = (
        "KYC records retained as mandated by PMLA 2002 (5-year minimum). "
        "PII fields anonymised in all other records."
    )
