"""Customer Management API"""
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.customer import Customer, CustomerStatus, CustomerSegment
from src.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter(prefix="/api/customers", tags=["Customers"])


def _generate_customer_id() -> str:
    return f"CUST{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"


def _assign_segment(annual_income: Optional[float]) -> CustomerSegment:
    if not annual_income:
        return CustomerSegment.MASS
    if annual_income >= 10_000_000:
        return CustomerSegment.UHNI
    if annual_income >= 5_000_000:
        return CustomerSegment.HNI
    if annual_income >= 1_000_000:
        return CustomerSegment.AFFLUENT
    if annual_income >= 300_000:
        return CustomerSegment.MASS_AFFLUENT
    return CustomerSegment.MASS


@router.post("/", response_model=CustomerResponse, status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(Customer).filter(Customer.mobile == data.mobile).first()
    if existing:
        raise HTTPException(status_code=409, detail="Customer with this mobile already exists")

    customer = Customer(
        customer_id=_generate_customer_id(),
        segment=_assign_segment(data.annual_income),
        **data.model_dump(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/", response_model=List[CustomerResponse])
def list_customers(
    status: Optional[CustomerStatus] = None,
    segment: Optional[CustomerSegment] = None,
    kyc_completed: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    if status:
        q = q.filter(Customer.status == status)
    if segment:
        q = q.filter(Customer.segment == segment)
    if kyc_completed is not None:
        q = q.filter(Customer.kyc_completed == kyc_completed)
    return q.order_by(Customer.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(
        (Customer.id == customer_id) | (Customer.customer_id == customer_id)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: str, data: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(
        (Customer.id == customer_id) | (Customer.customer_id == customer_id)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(customer, field, value)

    if data.annual_income is not None:
        customer.segment = _assign_segment(data.annual_income)

    db.commit()
    db.refresh(customer)
    return customer


@router.get("/search/by-mobile/{mobile}", response_model=CustomerResponse)
def find_by_mobile(mobile: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.mobile == mobile).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/search/by-pan/{pan}", response_model=CustomerResponse)
def find_by_pan(pan: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.pan_number == pan.upper()).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/analytics/segment-distribution", response_model=dict)
def segment_distribution(db: Session = Depends(get_db)):
    result = {}
    for seg in CustomerSegment:
        result[seg.value] = db.query(Customer).filter(Customer.segment == seg).count()
    return result
