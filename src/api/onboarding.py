"""Conversational Onboarding API"""
import json
import uuid
import secrets
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.onboarding import OnboardingSession, OnboardingMessage, OnboardingStage, MessageRole
from src.schemas.onboarding import (
    OnboardingStartRequest, ChatMessage, ChatResponse,
    OnboardingSessionResponse, ChatOption, PersonalizationRequest, PersonalizationResponse,
)
from src.services.conversation import conversation_service, STAGE_PROGRESS
from src.services.personalization import personalization_service
from src.services.lead_scoring import lead_scoring_service

router = APIRouter(prefix="/api/onboarding", tags=["Conversational Onboarding"])


@router.post("/start", response_model=ChatResponse)
def start_onboarding_session(data: OnboardingStartRequest, db: Session = Depends(get_db)):
    session_token = secrets.token_urlsafe(32)

    session = OnboardingSession(
        session_token=session_token,
        language=data.language,
        channel=data.channel,
        device_type=data.device_type,
        current_stage=OnboardingStage.WELCOME,
        collected_data=json.dumps({}),
        stages_completed=json.dumps([]),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    welcome = conversation_service.get_welcome_message(data.language, data.initial_intent)

    assistant_msg = OnboardingMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=welcome["message"],
        stage_at_message=OnboardingStage.WELCOME.value,
        suggestion_type="text",
    )
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        session_token=session_token,
        message=welcome["message"],
        message_type="text",
        current_stage=OnboardingStage.WELCOME,
        progress_percent=STAGE_PROGRESS[OnboardingStage.WELCOME],
    )


@router.post("/chat", response_model=ChatResponse)
def chat(data: ChatMessage, db: Session = Depends(get_db)):
    session = db.query(OnboardingSession).filter(
        OnboardingSession.session_token == data.session_token
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is no longer active")

    # Save user message
    user_msg = OnboardingMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content=data.message,
        stage_at_message=session.current_stage.value,
    )
    db.add(user_msg)

    # Build conversation history for AI
    history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in session.messages[-20:]  # last 20 turns for context
    ]

    collected = json.loads(session.collected_data or "{}")

    # Extract entities from message and merge into collected_data
    entities = conversation_service.extract_entities(data.message, session.current_stage)
    collected.update(entities)

    # Get AI response
    reply, new_stage, options = conversation_service.chat(
        session_id=session.id,
        user_message=data.message,
        conversation_history=history,
        current_stage=session.current_stage,
        collected_data=collected,
        language=session.language,
    )

    # Handle product selection if user picked an option
    if data.selected_option and session.current_stage == OnboardingStage.PRODUCT_SELECTION:
        session.product_selected = data.selected_option
        collected["product"] = data.selected_option
        kyc_msg = conversation_service.get_kyc_guidance_message(data.selected_option)
        reply = kyc_msg["message"]
        options_raw = kyc_msg.get("options", [])
        options = [ChatOption(**o) for o in options_raw] if options_raw else None
        new_stage = OnboardingStage.KYC_INITIATION

    # Update session state
    session.collected_data = json.dumps(collected)
    session.last_active_at = datetime.utcnow()

    if new_stage:
        completed = json.loads(session.stages_completed or "[]")
        if session.current_stage.value not in completed:
            completed.append(session.current_stage.value)
        session.stages_completed = json.dumps(completed)
        session.current_stage = new_stage

        if new_stage == OnboardingStage.ABANDONED:
            session.is_active = False
        elif new_stage == OnboardingStage.COMPLETED:
            session.is_active = False
            session.completed_at = datetime.utcnow()
            if session.started_at:
                delta = (session.completed_at - session.started_at).seconds // 60
                session.time_to_complete_minutes = delta

    # Inject product options at the right stage
    if session.current_stage == OnboardingStage.PRODUCT_SELECTION and options is None:
        options = [ChatOption(**o) for o in conversation_service.get_product_options()]

    # Save assistant message
    assistant_msg = OnboardingMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=reply,
        stage_at_message=session.current_stage.value,
        suggestion_type="options" if options else "text",
        options_provided=json.dumps([o.model_dump() for o in options]) if options else None,
    )
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        session_token=data.session_token,
        message=reply,
        message_type="options" if options else "text",
        options=options,
        current_stage=session.current_stage,
        progress_percent=STAGE_PROGRESS.get(session.current_stage, 0),
    )


@router.get("/session/{session_token}", response_model=OnboardingSessionResponse)
def get_session(session_token: str, db: Session = Depends(get_db)):
    session = db.query(OnboardingSession).filter(
        OnboardingSession.session_token == session_token
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/session/{session_token}/history", response_model=List[dict])
def get_session_history(session_token: str, db: Session = Depends(get_db)):
    session = db.query(OnboardingSession).filter(
        OnboardingSession.session_token == session_token
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        {
            "role": msg.role.value,
            "content": msg.content,
            "stage": msg.stage_at_message,
            "timestamp": msg.created_at.isoformat() if msg.created_at else None,
            "options": json.loads(msg.options_provided) if msg.options_provided else None,
        }
        for msg in session.messages
    ]


@router.post("/session/{session_token}/abandon")
def abandon_session(session_token: str, db: Session = Depends(get_db)):
    session = db.query(OnboardingSession).filter(
        OnboardingSession.session_token == session_token
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_active = False
    session.current_stage = OnboardingStage.ABANDONED
    db.commit()
    return {"message": "Session abandoned", "session_token": session_token}


@router.post("/personalize", response_model=PersonalizationResponse)
def personalize_for_customer(data: PersonalizationRequest, db: Session = Depends(get_db)):
    persona_tags = lead_scoring_service.detect_persona_tags(
        type("Lead", (), {"source": None, "interested_product": data.intent})(),
        data.context,
    )
    income = data.context.get("annual_income", 0)
    recommended = personalization_service.recommend_products(persona_tags, income)

    name = data.context.get("name", "there")
    message = personalization_service.generate_personalised_message(
        customer_name=name,
        persona_tags=persona_tags,
        recommended_products=recommended,
        intent=data.intent,
    )
    channel = personalization_service.detect_engagement_channel(
        persona_tags, data.context.get("preferred_channel")
    )
    nba = personalization_service.determine_next_best_action(
        lead_score=data.context.get("lead_score", 50),
        persona_tags=persona_tags,
        engagement_count=data.context.get("engagement_count", 0),
    )

    return PersonalizationResponse(
        persona_tags=persona_tags,
        recommended_products=recommended[:3],
        personalised_message=message,
        engagement_channel=channel,
        next_best_action=nba["action"],
        offer_details=nba,
    )


@router.get("/analytics/funnel", response_model=dict)
def onboarding_funnel(db: Session = Depends(get_db)):
    stages = [s.value for s in OnboardingStage if s != OnboardingStage.ABANDONED]
    funnel = {}
    for stage in stages:
        count = db.query(OnboardingSession).filter(
            OnboardingSession.current_stage == stage
        ).count()
        funnel[stage] = count

    total_started = db.query(OnboardingSession).count()
    total_completed = db.query(OnboardingSession).filter(
        OnboardingSession.current_stage == OnboardingStage.COMPLETED
    ).count()
    abandoned = db.query(OnboardingSession).filter(
        OnboardingSession.current_stage == OnboardingStage.ABANDONED
    ).count()

    return {
        "total_sessions": total_started,
        "completed": total_completed,
        "abandoned": abandoned,
        "completion_rate": round(total_completed / total_started * 100, 2) if total_started else 0,
        "stage_distribution": funnel,
    }
