from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from src.models.customer import CustomerSegment, CustomerStatus, RiskCategory


class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    mobile: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    nationality: str = "Indian"
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    annual_income: Optional[float] = None
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    preferred_language: str = "en"
    preferred_channel: Optional[str] = None
    source: Optional[str] = None


class CustomerCreate(CustomerBase):
    referral_code: Optional[str] = None


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    annual_income: Optional[float] = None
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_channel: Optional[str] = None
    segment: Optional[CustomerSegment] = None
    risk_category: Optional[RiskCategory] = None


class CustomerResponse(CustomerBase):
    id: str
    customer_id: Optional[str] = None
    ckyc_id: Optional[str] = None
    segment: CustomerSegment
    status: CustomerStatus
    risk_category: RiskCategory
    kyc_completed: bool
    ckyc_verified: bool
    kyc_expiry_date: Optional[datetime] = None
    rekyc_due_date: Optional[datetime] = None
    engagement_score: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
