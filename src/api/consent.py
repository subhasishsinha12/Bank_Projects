"""
DPDP Consent Management API
Covers the full DPDP Act 2023 data-subject lifecycle:
  • Consent creation, activation, withdrawal
  • Customer consent dashboard
  • Data Subject Requests (access, correction, erasure, portability)
  • Data breach registration and DPCI notification tracking
  • Compliance health-check endpoint
"""
import json
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.customer import Customer
from src.models.consent import (
    ConsentRecord, ConsentStatus, ConsentPurpose,
    DataSubjectRequest, DataBreachRecord, DataProcessingRecord,
    DSRType, DataCategory,
)
from src.schemas.consent import (
    ConsentRequestCreate, ConsentActivate, ConsentRevoke, ConsentResponse,
    ConsentDashboardResponse, DSRCreate, DSRResponse,
    BreachCreate, BreachResponse, ErasureResponse,
)
from src.services.consent_manager import consent_manager
from src.config import settings

router = APIRouter(prefix="/api/consent", tags=["DPDP Consent Management"])


# ------------------------------------------------------------------ #
# Consent Lifecycle
# ------------------------------------------------------------------ #

@router.post("/request", response_model=ConsentResponse, status_code=201)
def request_consent(
    data: ConsentRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a consent artefact for a customer.
    The customer must then explicitly activate it (via UI confirmation or OTP).
    """
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing = db.query(ConsentRecord).filter(
        ConsentRecord.customer_id == data.customer_id,
        ConsentRecord.purpose == data.purpose,
        ConsentRecord.status == ConsentStatus.ACTIVE,
        ConsentRecord.expires_at > datetime.utcnow(),
    ).first()
    if existing:
        return existing  # idempotent — return existing active consent

    record = consent_manager.create_consent(
        db=db,
        customer_id=data.customer_id,
        purpose=data.purpose,
        data_categories=data.data_categories,
        legal_basis=data.legal_basis,
        language=data.language,
        channel=data.channel,
        ip_address=request.client.host if request.client else None,
        expiry_days=data.expiry_days,
        data_processors=data.data_processors,
    )
    return record


@router.post("/activate", response_model=ConsentResponse)
def activate_consent(
    data: ConsentActivate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Customer explicitly activates a pending consent (e.g. after reading terms).
    In production this is triggered by a signed OTP confirmation or UI checkbox.
    """
    record = db.query(ConsentRecord).filter(ConsentRecord.id == data.consent_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Consent record not found")
    if record.status != ConsentStatus.PENDING:
        raise HTTPException(status_code=400,
                            detail=f"Consent is already {record.status.value}")
    return consent_manager.activate_consent(
        db, data.consent_id, actor=data.actor,
        ip=request.client.host if request.client else None,
    )


@router.post("/revoke", response_model=ConsentResponse)
def revoke_consent(
    data: ConsentRevoke,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Customer withdraws a specific consent. Per DPDP §6(4): withdrawal must
    be as easy as giving consent and must not affect prior lawful processing.
    """
    record = db.query(ConsentRecord).filter(ConsentRecord.id == data.consent_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Consent record not found")
    return consent_manager.revoke_consent(
        db, data.consent_id, reason=data.reason, actor="customer",
        ip=request.client.host if request.client else None,
    )


@router.post("/revoke-purpose", response_model=dict)
def revoke_all_for_purpose(
    customer_id: str,
    purpose: ConsentPurpose,
    db: Session = Depends(get_db),
):
    """Withdraw all active consents for a given purpose in one call."""
    count = consent_manager.revoke_all_for_purpose(db, customer_id, purpose)
    return {"revoked_count": count, "purpose": purpose.value, "customer_id": customer_id}


@router.get("/customer/{customer_id}", response_model=ConsentDashboardResponse)
def consent_dashboard(customer_id: str, db: Session = Depends(get_db)):
    """
    Customer-facing consent dashboard — shows all consents, their status,
    data processing count, and pending DSRs.
    DPDP §12: data principal's right to access information about processing.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return consent_manager.get_consent_dashboard(db, customer_id)


@router.get("/customer/{customer_id}/check", response_model=dict)
def check_consent(
    customer_id: str,
    purpose: ConsentPurpose,
    db: Session = Depends(get_db),
):
    """Check if a customer has active consent for a specific purpose."""
    has = consent_manager.has_active_consent(db, customer_id, purpose)
    return {
        "customer_id": customer_id,
        "purpose": purpose.value,
        "has_consent": has,
        "obtain_url": f"/api/consent/request" if not has else None,
    }


# ------------------------------------------------------------------ #
# Bulk consent (onboarding bundle)
# ------------------------------------------------------------------ #

@router.post("/bundle/{customer_id}", response_model=dict)
def create_onboarding_consent_bundle(
    customer_id: str,
    request: Request,
    language: str = "en",
    channel: str = "web",
    db: Session = Depends(get_db),
):
    """
    Creates and activates the standard consent bundle for new customer onboarding.
    Covers: KYC verification, product personalisation, and fraud prevention.
    Marketing consent is kept separate (opt-in only).
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    ip = request.client.host if request.client else None
    bundle = [
        (ConsentPurpose.KYC_VERIFICATION,
         [DataCategory.PERSONAL_IDENTITY, DataCategory.IDENTITY_DOCUMENTS,
          DataCategory.CONTACT_INFO, DataCategory.BIOMETRIC]),
        (ConsentPurpose.PRODUCT_PERSONALISATION,
         [DataCategory.PERSONAL_IDENTITY, DataCategory.FINANCIAL_DATA,
          DataCategory.BEHAVIOURAL]),
        (ConsentPurpose.FRAUD_PREVENTION,
         [DataCategory.PERSONAL_IDENTITY, DataCategory.DEVICE_DATA,
          DataCategory.BEHAVIOURAL]),
    ]
    created = []
    for purpose, categories in bundle:
        existing = db.query(ConsentRecord).filter(
            ConsentRecord.customer_id == customer_id,
            ConsentRecord.purpose == purpose,
            ConsentRecord.status == ConsentStatus.ACTIVE,
            ConsentRecord.expires_at > datetime.utcnow(),
        ).first()
        if existing:
            created.append({"purpose": purpose.value, "status": "already_active",
                            "consent_id": existing.consent_id})
            continue
        record = consent_manager.create_consent(
            db, customer_id, purpose, categories,
            language=language, channel=channel, ip_address=ip,
        )
        consent_manager.activate_consent(db, record.id, actor="customer", ip=ip)
        created.append({"purpose": purpose.value, "status": "activated",
                        "consent_id": record.consent_id})

    return {"customer_id": customer_id, "consents_created": len(created), "bundle": created}


# ------------------------------------------------------------------ #
# Data Subject Requests (DPDP §12-17)
# ------------------------------------------------------------------ #

@router.post("/dsr", response_model=DSRResponse, status_code=201)
def submit_dsr(data: DSRCreate, db: Session = Depends(get_db)):
    """Submit a Data Subject Request — access, correction, erasure, or grievance."""
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    dsr = consent_manager.submit_dsr(db, data.customer_id, data.request_type, data.description)
    return dsr


@router.get("/dsr/customer/{customer_id}", response_model=List[DSRResponse])
def list_customer_dsrs(customer_id: str, db: Session = Depends(get_db)):
    return db.query(DataSubjectRequest).filter(
        DataSubjectRequest.customer_id == customer_id
    ).order_by(DataSubjectRequest.created_at.desc()).all()


@router.post("/dsr/{dsr_id}/resolve", response_model=DSRResponse)
def resolve_dsr(
    dsr_id: str,
    resolution_note: str,
    resolved_by: str = "compliance_officer",
    db: Session = Depends(get_db),
):
    try:
        return consent_manager.resolve_dsr(db, dsr_id, resolution_note, resolved_by)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/dsr/overdue", response_model=List[dict])
def list_overdue_dsrs(db: Session = Depends(get_db)):
    """DSRs past their 30-day resolution deadline — escalation required."""
    now = datetime.utcnow()
    overdue = db.query(DataSubjectRequest).filter(
        DataSubjectRequest.status.in_(["received", "in_progress"]),
        DataSubjectRequest.due_date < now,
    ).all()
    return [
        {
            "dsr_id": d.dsr_id,
            "customer_id": d.customer_id,
            "request_type": d.request_type.value,
            "due_date": d.due_date.isoformat() if d.due_date else None,
            "days_overdue": (now - d.due_date).days if d.due_date else None,
        }
        for d in overdue
    ]


# ------------------------------------------------------------------ #
# Right to Erasure (DPDP §14)
# ------------------------------------------------------------------ #

@router.delete("/customer/{customer_id}/erase", response_model=ErasureResponse)
def erase_customer_data(customer_id: str, db: Session = Depends(get_db)):
    """
    Anonymise customer PII across all mutable records.
    KYC records are retained (PMLA mandates 5 years).
    All active consents are revoked.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    result = consent_manager.execute_erasure(db, customer_id)
    dsr = consent_manager.submit_dsr(
        db, customer_id, DSRType.ERASURE,
        description="Erasure executed via API",
    )
    consent_manager.resolve_dsr(db, dsr.dsr_id, "Erasure completed", "system")
    return ErasureResponse(
        customer_id=customer_id,
        pii_fields_anonymised=result["pii_fields_anonymised"],
        consents_revoked=result["consents_revoked"],
        message="Customer PII anonymised. KYC records retained per PMLA mandate.",
    )


# ------------------------------------------------------------------ #
# Data Processing Audit Trail
# ------------------------------------------------------------------ #

@router.get("/processing-log/{customer_id}", response_model=List[dict])
def processing_log(
    customer_id: str,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Audit log of every time this customer's data was processed."""
    records = db.query(DataProcessingRecord).filter(
        DataProcessingRecord.customer_id == customer_id
    ).order_by(DataProcessingRecord.created_at.desc()).limit(limit).all()
    return [
        {
            "operation": r.operation,
            "data_categories": json.loads(r.data_categories or "[]"),
            "api_endpoint": r.api_endpoint,
            "legal_basis": r.legal_basis,
            "processed_by": r.processed_by,
            "third_party": r.third_party,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


# ------------------------------------------------------------------ #
# Data Breach (DPDP §8(6))
# ------------------------------------------------------------------ #

@router.post("/breach", response_model=BreachResponse, status_code=201)
def register_breach(data: BreachCreate, db: Session = Depends(get_db)):
    """Register a data breach. DPDP mandates DPCI notification within 72 hours."""
    breach = consent_manager.register_breach(
        db=db,
        breach_type=data.breach_type,
        data_categories=data.data_categories_affected,
        estimated_records=data.estimated_records_affected,
        description=data.description,
        discovered_at=data.discovered_at,
        reported_by=data.reported_by,
    )
    return breach


@router.post("/breach/{breach_ref}/notify-dpci", response_model=BreachResponse)
def notify_dpci(breach_ref: str, db: Session = Depends(get_db)):
    breach = db.query(DataBreachRecord).filter(
        DataBreachRecord.breach_ref == breach_ref
    ).first()
    if not breach:
        raise HTTPException(status_code=404, detail="Breach record not found")
    breach.dpci_notified_at = datetime.utcnow()
    breach.status = "notified"
    db.commit()
    db.refresh(breach)
    return breach


@router.get("/breach/pending-notification", response_model=List[dict])
def breaches_pending_notification(db: Session = Depends(get_db)):
    """Breaches past their 72-hour notification deadline."""
    now = datetime.utcnow()
    pending = db.query(DataBreachRecord).filter(
        DataBreachRecord.dpci_notified_at.is_(None),
        DataBreachRecord.notification_due < now,
    ).all()
    return [
        {
            "breach_ref": b.breach_ref,
            "breach_type": b.breach_type,
            "notification_due": b.notification_due.isoformat() if b.notification_due else None,
            "hours_overdue": round((now - b.notification_due).total_seconds() / 3600, 1)
                             if b.notification_due else None,
            "estimated_records": b.estimated_records_affected,
        }
        for b in pending
    ]


# ------------------------------------------------------------------ #
# Compliance Health Check
# ------------------------------------------------------------------ #

@router.get("/compliance/health", response_model=dict)
def compliance_health(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    total_active  = db.query(ConsentRecord).filter(ConsentRecord.status == ConsentStatus.ACTIVE).count()
    expiring_soon = db.query(ConsentRecord).filter(
        ConsentRecord.status == ConsentStatus.ACTIVE,
        ConsentRecord.expires_at.between(now, now + timedelta(days=30)),
    ).count()
    overdue_dsrs  = db.query(DataSubjectRequest).filter(
        DataSubjectRequest.status.in_(["received", "in_progress"]),
        DataSubjectRequest.due_date < now,
    ).count()
    unnotified_breaches = db.query(DataBreachRecord).filter(
        DataBreachRecord.dpci_notified_at.is_(None),
        DataBreachRecord.notification_due < now,
    ).count()

    return {
        "dpdp_compliance_version": settings.dpdp_consent_version,
        "data_fiduciary": settings.dpdp_data_fiduciary_name,
        "dpo_email": settings.dpdp_dpo_email,
        "active_consents": total_active,
        "consents_expiring_in_30_days": expiring_soon,
        "overdue_dsrs": overdue_dsrs,
        "breaches_pending_dpci_notification": unnotified_breaches,
        "overall_status": "COMPLIANT" if overdue_dsrs == 0 and unnotified_breaches == 0
                          else "ACTION_REQUIRED",
        "checked_at": now.isoformat(),
    }
