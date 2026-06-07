from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.models.lead import LeadStatus, LeadSource, LeadQuality


class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    mobile: str
    city: Optional[str] = None
    state: Optional[str] = None
    source: LeadSource = LeadSource.WEBSITE
    interested_product: Optional[str] = None
    interested_amount: Optional[float] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    assigned_to: Optional[str] = None
    next_follow_up_date: Optional[datetime] = None
    personalised_message: Optional[str] = None
    loss_reason: Optional[str] = None


class LeadScoreRequest(BaseModel):
    lead_id: str
    additional_signals: Optional[Dict[str, Any]] = None


class LeadResponse(BaseModel):
    id: str
    lead_id: str
    name: str
    email: Optional[str] = None
    mobile: str
    city: Optional[str] = None
    state: Optional[str] = None
    source: LeadSource
    status: LeadStatus
    quality: LeadQuality
    lead_score: int
    interested_product: Optional[str] = None
    persona_tags: Optional[str] = None
    recommended_products: Optional[str] = None
    personalised_message: Optional[str] = None
    assigned_to: Optional[str] = None
    next_follow_up_date: Optional[datetime] = None
    engagement_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class LeadActivityCreate(BaseModel):
    lead_id: str
    activity_type: str
    activity_description: Optional[str] = None
    channel: Optional[str] = None
    outcome: Optional[str] = None
    performed_by: Optional[str] = None


class LeadActivityResponse(BaseModel):
    id: str
    lead_id: str
    activity_type: str
    activity_description: Optional[str] = None
    channel: Optional[str] = None
    outcome: Optional[str] = None
    score_impact: int
    performed_by: Optional[str] = None
    performed_at: datetime

    class Config:
        from_attributes = True


class BulkLeadImport(BaseModel):
    leads: List[LeadCreate]
    source: LeadSource = LeadSource.DIGITAL_CAMPAIGN
