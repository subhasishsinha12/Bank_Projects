"""CKYC (Central KYC Registry) Integration API"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.customer import Customer
from src.schemas.kyc import CKYCSearchRequest, CKYCUpdateRequest, CKYCResponse
from src.services.ckyc_client import ckyc_client

router = APIRouter(prefix="/api/ckyc", tags=["CKYC Registry"])


@router.post("/search", response_model=CKYCResponse)
def search_ckyc(data: CKYCSearchRequest):
    """
    Search the Central KYC Registry for an existing KYC record.
    Supports search by PAN, Aadhaar, or demographics.
    """
    if data.pan_number:
        result = ckyc_client.search_by_pan(data.pan_number)
    elif data.aadhaar_number:
        result = ckyc_client.search_by_aadhaar(data.aadhaar_number)
    elif data.full_name and data.date_of_birth:
        result = ckyc_client.search_by_demographics(
            data.full_name, data.date_of_birth, data.mobile
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: pan_number, aadhaar_number, or full_name+date_of_birth",
        )

    return CKYCResponse(
        ckyc_id=result.get("ckyc_id"),
        found=result.get("found", False),
        customer_data=result.get("customer_data"),
        kyc_status=result.get("kyc_status"),
        last_updated=result.get("last_updated"),
        institution=result.get("institution"),
    )


@router.post("/fetch/{ckyc_id}", response_model=dict)
def fetch_ckyc_record(ckyc_id: str):
    """Fetch a complete KYC record from CKYC Registry by KIN (14-digit identifier)."""
    if len(ckyc_id) != 14 or not ckyc_id.isdigit():
        raise HTTPException(status_code=400, detail="CKYC KIN must be a 14-digit number")
    return ckyc_client.fetch_ckyc_record(ckyc_id)


@router.post("/register/{customer_id}", response_model=dict)
def register_customer_ckyc(customer_id: str, db: Session = Depends(get_db)):
    """
    Register a KYC-completed customer in the Central KYC Registry.
    Customer must have completed KYC before registration.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not customer.kyc_completed:
        raise HTTPException(status_code=400, detail="Customer KYC is not yet complete")
    if customer.ckyc_verified:
        return {
            "message": "Customer already registered in CKYC Registry",
            "ckyc_id": customer.ckyc_id,
        }

    customer_data = {
        "full_name": customer.full_name,
        "date_of_birth": customer.date_of_birth,
        "gender": customer.gender,
        "pan_number": customer.pan_number,
        "aadhaar_number": customer.aadhaar_number,
        "mobile": customer.mobile,
        "email": customer.email,
        "address": f"{customer.address_line1}, {customer.city}, {customer.state} - {customer.pincode}",
        "nationality": customer.nationality,
    }

    result = ckyc_client.register_customer(customer_data, [])

    if result.get("success"):
        customer.ckyc_id = result["ckyc_id"]
        customer.ckyc_verified = True
        db.commit()

    return result


@router.post("/prefill/{customer_id}", response_model=dict)
def prefill_from_ckyc(
    customer_id: str,
    pan_number: Optional[str] = None,
    aadhaar_number: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Fetch existing CKYC data to pre-fill the customer's profile during onboarding.
    Reduces friction for returning KYC holders.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    identifier = pan_number or aadhaar_number
    if not identifier:
        raise HTTPException(status_code=400, detail="Provide pan_number or aadhaar_number")

    if pan_number:
        result = ckyc_client.search_by_pan(pan_number)
    else:
        result = ckyc_client.search_by_aadhaar(aadhaar_number)

    if not result.get("found"):
        return {"found": False, "message": "No CKYC record found. Proceeding with fresh KYC."}

    ckyc_data = result.get("customer_data", {})
    ckyc_id = result.get("ckyc_id")

    # Pre-fill customer fields from CKYC data where not already set
    if ckyc_id and not customer.ckyc_id:
        customer.ckyc_id = ckyc_id
        customer.ckyc_verified = True

    if ckyc_data.get("pan_number") and not customer.pan_number:
        customer.pan_number = ckyc_data["pan_number"]

    db.commit()

    return {
        "found": True,
        "ckyc_id": ckyc_id,
        "prefilled_fields": list(ckyc_data.keys()),
        "message": "CKYC data fetched successfully. Profile pre-filled.",
        "kyc_status": result.get("kyc_status"),
        "customer_data": ckyc_data,
    }


@router.post("/update", response_model=dict)
def update_ckyc_record(data: CKYCUpdateRequest, db: Session = Depends(get_db)):
    """
    Submit a change request to the CKYC Registry for updated customer details.
    Common updates: address change, contact change, name correction.
    """
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not customer.ckyc_id:
        raise HTTPException(
            status_code=400,
            detail="Customer is not registered in CKYC Registry. Use /register first.",
        )

    result = ckyc_client.update_customer(customer.ckyc_id, data.updated_fields)

    if result.get("success"):
        for field, value in data.updated_fields.items():
            if hasattr(customer, field):
                setattr(customer, field, value)
        db.commit()

    return result


@router.get("/customer/{customer_id}/status", response_model=dict)
def customer_ckyc_status(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "customer_id": customer_id,
        "ckyc_registered": customer.ckyc_verified,
        "ckyc_id": customer.ckyc_id,
        "kyc_completed": customer.kyc_completed,
        "kyc_completion_date": customer.kyc_completion_date.isoformat() if customer.kyc_completion_date else None,
        "kyc_expiry_date": customer.kyc_expiry_date.isoformat() if customer.kyc_expiry_date else None,
    }
