from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.models.onboarding import OnboardingStage, MessageRole


class OnboardingStartRequest(BaseModel):
    channel: str = "web"
    language: str = "en"
    device_type: Optional[str] = None
    utm_source: Optional[str] = None
    referral_code: Optional[str] = None
    initial_intent: Optional[str] = None  # savings_account, loan, fd, etc.


class ChatMessage(BaseModel):
    session_token: str
    message: str
    message_type: str = "text"  # text, voice_transcript, selection
    selected_option: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatOption(BaseModel):
    label: str
    value: str
    description: Optional[str] = None
    icon: Optional[str] = None


class ChatResponse(BaseModel):
    session_token: str
    message: str
    message_type: str = "text"  # text, options, document_upload, otp, redirect
    options: Optional[List[ChatOption]] = None
    current_stage: OnboardingStage
    progress_percent: int
    next_action: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OnboardingSessionResponse(BaseModel):
    id: str
    session_token: str
    customer_id: Optional[str] = None
    current_stage: OnboardingStage
    language: str
    is_active: bool
    stages_completed: str
    product_selected: Optional[str] = None
    persona: Optional[str] = None
    started_at: datetime
    last_active_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonalizationRequest(BaseModel):
    customer_id: Optional[str] = None
    lead_id: Optional[str] = None
    context: Dict[str, Any]
    intent: Optional[str] = None


class PersonalizationResponse(BaseModel):
    persona_tags: List[str]
    recommended_products: List[Dict[str, Any]]
    personalised_message: str
    engagement_channel: str
    next_best_action: str
    offer_details: Optional[Dict[str, Any]] = None
