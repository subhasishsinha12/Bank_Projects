"""Lead Management & Scoring API"""
import json
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.lead import Lead, LeadActivity, LeadStatus, LeadQuality, LeadSource
from src.models.customer import Customer
from src.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse, LeadActivityCreate,
    LeadActivityResponse, LeadScoreRequest, BulkLeadImport,
)
from src.services.lead_scoring import lead_scoring_service
from src.services.personalization import personalization_service

router = APIRouter(prefix="/api/leads", tags=["Lead Management"])


def _generate_lead_id() -> str:
    return f"LEAD{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


@router.post("/", response_model=LeadResponse, status_code=201)
def create_lead(data: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(
        lead_id=_generate_lead_id(),
        name=data.name,
        email=data.email,
        mobile=data.mobile,
        city=data.city,
        state=data.state,
        source=data.source,
        interested_product=data.interested_product,
        interested_amount=data.interested_amount,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
    )

    score_result = lead_scoring_service.compute_score(lead)
    lead.lead_score = score_result["score"]
    lead.quality = score_result["quality"]
    lead.score_breakdown = json.dumps(score_result["breakdown"])

    persona_tags = lead_scoring_service.detect_persona_tags(lead)
    lead.persona_tags = json.dumps(persona_tags)

    recommended = personalization_service.recommend_products(persona_tags)
    lead.recommended_products = json.dumps([p["product_id"] for p in recommended])

    if recommended:
        lead.personalised_message = personalization_service.generate_personalised_message(
            customer_name=data.name.split()[0],
            persona_tags=persona_tags,
            recommended_products=recommended,
            intent=data.interested_product,
        )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    activity = LeadActivity(
        lead_id=lead.id,
        activity_type="lead_created",
        activity_description=f"Lead created via {data.source.value}",
        channel=data.source.value,
        score_impact=lead.lead_score,
    )
    db.add(activity)
    db.commit()

    return lead


@router.get("/", response_model=List[LeadResponse])
def list_leads(
    status: Optional[LeadStatus] = None,
    quality: Optional[LeadQuality] = None,
    source: Optional[LeadSource] = None,
    assigned_to: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Lead)
    if status:
        q = q.filter(Lead.status == status)
    if quality:
        q = q.filter(Lead.quality == quality)
    if source:
        q = q.filter(Lead.source == source)
    if assigned_to:
        q = q.filter(Lead.assigned_to == assigned_to)
    return q.order_by(Lead.lead_score.desc()).offset(offset).limit(limit).all()


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, data: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(lead, field, value)

    if data.status == LeadStatus.CONVERTED:
        lead.converted_at = datetime.utcnow()

    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/rescore", response_model=dict)
def rescore_lead(lead_id: str, request: LeadScoreRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    result = lead_scoring_service.compute_score(lead, request.additional_signals)
    lead.lead_score = result["score"]
    lead.quality = result["quality"]
    lead.score_breakdown = json.dumps(result["breakdown"])

    if request.additional_signals:
        tags = lead_scoring_service.detect_persona_tags(lead, request.additional_signals)
        lead.persona_tags = json.dumps(tags)
        recommended = personalization_service.recommend_products(
            tags, request.additional_signals.get("annual_income", 0)
        )
        lead.recommended_products = json.dumps([p["product_id"] for p in recommended])

    db.commit()
    return {
        "lead_id": lead_id,
        "new_score": result["score"],
        "quality": result["quality"].value,
        "breakdown": result["breakdown"],
    }


@router.post("/{lead_id}/activity", response_model=LeadActivityResponse)
def log_activity(lead_id: str, data: LeadActivityCreate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    ACTIVITY_SCORE_MAP = {
        "email_opened": 5,
        "link_clicked": 8,
        "form_filled": 15,
        "call_connected": 20,
        "document_uploaded": 25,
        "page_view": 2,
    }
    score_impact = ACTIVITY_SCORE_MAP.get(data.activity_type, 0)

    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=data.activity_type,
        activity_description=data.activity_description,
        channel=data.channel,
        outcome=data.outcome,
        score_impact=score_impact,
        performed_by=data.performed_by,
    )
    db.add(activity)

    lead.engagement_count = (lead.engagement_count or 0) + 1
    lead.last_contact_date = datetime.utcnow()
    lead.lead_score = min(100, (lead.lead_score or 0) + score_impact)
    lead.quality = lead_scoring_service._classify_quality(lead.lead_score)

    db.commit()
    db.refresh(activity)
    return activity


@router.post("/bulk-import", response_model=dict)
def bulk_import_leads(data: BulkLeadImport, db: Session = Depends(get_db)):
    created, failed = 0, 0
    for lead_data in data.leads:
        try:
            lead_data.source = data.source
            existing = db.query(Lead).filter(Lead.mobile == lead_data.mobile).first()
            if existing:
                failed += 1
                continue
            lead = Lead(
                lead_id=_generate_lead_id(),
                **lead_data.model_dump(),
            )
            score_result = lead_scoring_service.compute_score(lead)
            lead.lead_score = score_result["score"]
            lead.quality = score_result["quality"]
            lead.score_breakdown = json.dumps(score_result["breakdown"])
            db.add(lead)
            created += 1
        except Exception:
            failed += 1

    db.commit()
    return {"created": created, "failed": failed, "total": len(data.leads)}


@router.get("/analytics/summary", response_model=dict)
def leads_analytics_summary(db: Session = Depends(get_db)):
    total = db.query(Lead).count()
    hot = db.query(Lead).filter(Lead.quality == LeadQuality.HOT).count()
    warm = db.query(Lead).filter(Lead.quality == LeadQuality.WARM).count()
    cold = db.query(Lead).filter(Lead.quality == LeadQuality.COLD).count()
    converted = db.query(Lead).filter(Lead.status == LeadStatus.CONVERTED).count()

    conversion_rate = round((converted / total * 100), 2) if total > 0 else 0

    pipeline_value = sum(
        row[0] for row in db.query(Lead.interested_amount).filter(
            Lead.interested_amount.isnot(None)
        ).all()
    )

    return {
        "total_leads": total,
        "by_quality": {"hot": hot, "warm": warm, "cold": cold},
        "converted": converted,
        "conversion_rate_percent": conversion_rate,
        "pipeline_value": pipeline_value,
    }
