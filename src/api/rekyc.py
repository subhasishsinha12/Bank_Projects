"""Re-KYC (Periodic KYC Update) API"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.customer import Customer
from src.models.kyc import ReKYCRequest
from src.schemas.kyc import ReKYCInitiateRequest, ReKYCRequestResponse
from src.services.kyc_processor import kyc_processor
from src.config import settings

router = APIRouter(prefix="/api/rekyc", tags=["Re-KYC"])


@router.post("/initiate", response_model=ReKYCRequestResponse, status_code=201)
def initiate_rekyc(data: ReKYCInitiateRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing = db.query(ReKYCRequest).filter(
        ReKYCRequest.customer_id == data.customer_id,
        ReKYCRequest.status.in_(["pending", "initiated"]),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A Re-KYC request is already in progress")

    schedule = kyc_processor.schedule_rekyc(customer, data.trigger_reason)

    rekyc = ReKYCRequest(
        customer_id=data.customer_id,
        status="initiated",
        trigger_reason=data.trigger_reason,
        due_date=schedule["due_date"],
        initiated_at=datetime.utcnow(),
        previous_kyc_date=customer.kyc_completion_date,
        reminder_channel=data.preferred_channel,
    )
    db.add(rekyc)

    customer.rekyc_due_date = schedule["due_date"]
    db.commit()
    db.refresh(rekyc)
    return rekyc


@router.get("/customer/{customer_id}", response_model=List[ReKYCRequestResponse])
def list_customer_rekyc_requests(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return db.query(ReKYCRequest).filter(ReKYCRequest.customer_id == customer_id).all()


@router.post("/{request_id}/complete", response_model=ReKYCRequestResponse)
def complete_rekyc(request_id: str, db: Session = Depends(get_db)):
    rekyc = db.query(ReKYCRequest).filter(ReKYCRequest.id == request_id).first()
    if not rekyc:
        raise HTTPException(status_code=404, detail="Re-KYC request not found")

    rekyc.status = "completed"
    rekyc.completed_at = datetime.utcnow()

    customer = db.query(Customer).filter(Customer.id == rekyc.customer_id).first()
    if customer:
        customer.kyc_completion_date = datetime.utcnow()
        customer.kyc_expiry_date = datetime.utcnow() + timedelta(days=settings.rekyc_validity_years * 365)
        customer.rekyc_due_date = customer.kyc_expiry_date

    db.commit()
    db.refresh(rekyc)
    return rekyc


@router.get("/overdue", response_model=List[dict])
def list_overdue_rekyc(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """List all customers whose Re-KYC is overdue."""
    now = datetime.utcnow()
    overdue_customers = db.query(Customer).filter(
        Customer.kyc_completed == True,
        Customer.rekyc_due_date < now,
    ).limit(limit).all()

    return [
        {
            "customer_id": c.id,
            "customer_name": c.full_name,
            "mobile": c.mobile,
            "email": c.email,
            "rekyc_due_date": c.rekyc_due_date.isoformat() if c.rekyc_due_date else None,
            "days_overdue": (now - c.rekyc_due_date).days if c.rekyc_due_date else None,
            "preferred_channel": c.preferred_channel,
        }
        for c in overdue_customers
    ]


@router.get("/due-soon", response_model=List[dict])
def list_rekyc_due_soon(
    days_ahead: int = Query(default=90, description="Customers whose Re-KYC is due within these many days"),
    db: Session = Depends(get_db),
):
    """List customers whose Re-KYC is due within the specified window."""
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days_ahead)
    customers = db.query(Customer).filter(
        Customer.kyc_completed == True,
        Customer.rekyc_due_date.between(now, cutoff),
    ).all()

    return [
        {
            "customer_id": c.id,
            "customer_name": c.full_name,
            "mobile": c.mobile,
            "email": c.email,
            "rekyc_due_date": c.rekyc_due_date.isoformat() if c.rekyc_due_date else None,
            "days_remaining": (c.rekyc_due_date - now).days if c.rekyc_due_date else None,
            "preferred_channel": c.preferred_channel,
        }
        for c in customers
    ]


@router.post("/send-reminders", response_model=dict)
def send_rekyc_reminders(db: Session = Depends(get_db)):
    """
    Trigger reminders for customers whose Re-KYC is due within 90 days.
    In production, this integrates with SMS/email/WhatsApp gateway.
    """
    now = datetime.utcnow()
    reminder_window = now + timedelta(days=settings.rekyc_reminder_days)

    customers = db.query(Customer).filter(
        Customer.kyc_completed == True,
        Customer.rekyc_due_date.between(now, reminder_window),
    ).all()

    sent_count = 0
    for customer in customers:
        rekyc_req = db.query(ReKYCRequest).filter(
            ReKYCRequest.customer_id == customer.id,
            ReKYCRequest.status.in_(["pending", "initiated"]),
        ).first()

        if not rekyc_req:
            rekyc_req = ReKYCRequest(
                customer_id=customer.id,
                status="pending",
                trigger_reason="periodic_reminder",
                due_date=customer.rekyc_due_date,
                reminder_channel=customer.preferred_channel or "email",
            )
            db.add(rekyc_req)

        rekyc_req.reminder_sent_at = datetime.utcnow()
        rekyc_req.reminder_count = (rekyc_req.reminder_count or 0) + 1
        sent_count += 1

    db.commit()
    return {
        "reminders_sent": sent_count,
        "window_days": settings.rekyc_reminder_days,
        "timestamp": now.isoformat(),
    }


@router.get("/analytics", response_model=dict)
def rekyc_analytics(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    total_kyc_done = db.query(Customer).filter(Customer.kyc_completed == True).count()
    overdue = db.query(Customer).filter(
        Customer.kyc_completed == True,
        Customer.rekyc_due_date < now,
    ).count()
    due_90d = db.query(Customer).filter(
        Customer.kyc_completed == True,
        Customer.rekyc_due_date.between(now, now + timedelta(days=90)),
    ).count()
    completed_rekyc = db.query(ReKYCRequest).filter(ReKYCRequest.status == "completed").count()

    return {
        "total_customers_with_kyc": total_kyc_done,
        "rekyc_overdue": overdue,
        "rekyc_due_in_90_days": due_90d,
        "rekyc_completed_total": completed_rekyc,
    }
