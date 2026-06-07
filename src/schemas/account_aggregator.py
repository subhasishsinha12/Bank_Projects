from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.models.account_aggregator import FIType, FetchType, AAConsentStatus, AADataFetchStatus


class AAConsentInitiate(BaseModel):
    customer_id: str
    customer_aa_handle: str       # e.g. customer@finvu
    aa_provider: str = "finvu"   # finvu | onemoney | phonepe | cams
    fi_types: List[FIType] = [FIType.DEPOSIT]
    purpose: str = "credit_assessment"
    fetch_type: FetchType = FetchType.ONE_TIME
    data_date_range_months: int = Field(default=6, ge=1, le=24)


class AAConsentCallback(BaseModel):
    """Webhook payload received from AA when customer approves/rejects."""
    consent_handle: str
    status: AAConsentStatus
    consent_id: Optional[str] = None
    signed_consent: Optional[str] = None
    rejection_reason: Optional[str] = None
    timestamp: Optional[str] = None


class AADataFetchRequest(BaseModel):
    consent_artefact_id: str      # internal DB id of AAConsentArtefact


class AAConsentResponse(BaseModel):
    id: str
    txn_id: str
    consent_handle: str
    customer_id: str
    aa_id: Optional[str] = None
    fi_types: Optional[str] = None
    status: AAConsentStatus
    redirect_url: Optional[str] = None
    consent_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AADataFetchResponse(BaseModel):
    id: str
    consent_id: str
    session_id: Optional[str] = None
    status: AADataFetchStatus
    accounts_found: int
    fi_types_fetched: Optional[str] = None
    fetch_error: Optional[str] = None
    requested_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LinkedAccountResponse(BaseModel):
    id: str
    fip_id: Optional[str] = None
    fip_name: Optional[str] = None
    masked_account_number: Optional[str] = None
    account_type: Optional[str] = None
    fi_type: Optional[FIType] = None
    currency: str
    current_balance: Optional[float] = None
    avg_monthly_balance: Optional[float] = None
    account_opened: Optional[str] = None

    class Config:
        from_attributes = True


class FinancialSummaryResponse(BaseModel):
    id: str
    customer_id: str
    verified_monthly_income: Optional[float] = None
    income_confidence: Optional[float] = None
    employer_verified: bool
    employer_name_aa: Optional[str] = None
    avg_monthly_balance: Optional[float] = None
    min_monthly_balance_6m: Optional[float] = None
    max_monthly_balance_6m: Optional[float] = None
    total_monthly_obligations: Optional[float] = None
    obligation_count: int
    debt_to_income_ratio: Optional[float] = None
    total_accounts_found: int
    total_fips_linked: int
    pre_approved_personal_loan: Optional[float] = None
    pre_approved_credit_card: Optional[float] = None
    pre_approved_home_loan: Optional[float] = None
    credit_behaviour_score: Optional[float] = None
    bounced_cheques_6m: int
    returned_emi_count_6m: int
    analysis_from: Optional[str] = None
    analysis_to: Optional[str] = None
    computed_at: datetime

    class Config:
        from_attributes = True


class PreApprovalResponse(BaseModel):
    customer_id: str
    verified_income_monthly: Optional[float] = None
    income_confidence_pct: Optional[float] = None
    employer: Optional[str] = None
    pre_approved_products: List[Dict[str, Any]]
    debt_to_income_ratio: Optional[float] = None
    credit_behaviour_score: Optional[float] = None
    data_source: str = "account_aggregator"
    disclaimer: str = (
        "Pre-approval is indicative. Final sanction subject to credit bureau check, "
        "internal credit policy, and RBI guidelines."
    )
