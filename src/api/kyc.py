"""KYC Document Management API"""
import json
import os
import shutil
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.customer import Customer
from src.models.kyc import KYCDocument, KYCVerification, VerificationStatus, DocumentType, KYCType
from src.schemas.kyc import (
    KYCDocumentCreate, KYCDocumentResponse,
    AadhaarOTPRequest, AadhaarOTPVerify, PANVerifyRequest,
    KYCStatusResponse,
)
from src.services.kyc_processor import kyc_processor
from src.config import settings

router = APIRouter(prefix="/api/kyc", tags=["KYC Management"])

UPLOAD_DIR = "uploads/kyc"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=KYCDocumentResponse)
async def upload_document(
    customer_id: str = Form(...),
    document_type: DocumentType = Form(...),
    document_number: str = Form(None),
    document_expiry: str = Form(None),
    kyc_type: KYCType = Form(KYCType.FRESH),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

    cust_dir = os.path.join(UPLOAD_DIR, customer_id)
    os.makedirs(cust_dir, exist_ok=True)
    file_name = f"{document_type.value}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = os.path.join(cust_dir, file_name)

    with open(file_path, "wb") as f:
        f.write(content)

    extracted = kyc_processor.extract_document_data(file_path, document_type)

    doc = KYCDocument(
        customer_id=customer_id,
        kyc_type=kyc_type,
        document_type=document_type,
        document_number=document_number or extracted.get("pan_number") or extracted.get("aadhaar_number"),
        document_expiry=document_expiry,
        file_path=file_path,
        file_name=file_name,
        file_size=len(content),
        mime_type=file.content_type,
        extracted_data=json.dumps(extracted),
        ocr_confidence=extracted.get("confidence"),
        verification_status=VerificationStatus.PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/customer/{customer_id}", response_model=List[KYCDocumentResponse])
def list_customer_documents(customer_id: str, db: Session = Depends(get_db)):
    return db.query(KYCDocument).filter(KYCDocument.customer_id == customer_id).all()


@router.get("/customer/{customer_id}/status", response_model=KYCStatusResponse)
def kyc_status(customer_id: str, product: str = "default", db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    docs = db.query(KYCDocument).filter(KYCDocument.customer_id == customer_id).all()
    status = kyc_processor.compute_kyc_status(docs, product)

    return KYCStatusResponse(
        customer_id=customer_id,
        overall_status=status["overall_status"],
        kyc_completed=customer.kyc_completed,
        ckyc_verified=customer.ckyc_verified,
        documents_submitted=status["submitted_count"],
        documents_verified=status["verified_count"],
        pending_documents=status["pending_documents"],
        kyc_expiry_date=customer.kyc_expiry_date,
        rekyc_due_date=customer.rekyc_due_date,
        is_rekyc_overdue=kyc_processor.is_rekyc_overdue(customer),
    )


@router.post("/aadhaar/send-otp", response_model=dict)
def send_aadhaar_otp(data: AadhaarOTPRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = kyc_processor.initiate_aadhaar_otp(data.aadhaar_number)
    return result


@router.post("/aadhaar/verify-otp", response_model=dict)
def verify_aadhaar_otp(data: AadhaarOTPVerify, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = kyc_processor.verify_aadhaar_otp(
        data.aadhaar_number, data.otp, data.transaction_id
    )

    if result.get("verified"):
        customer.aadhaar_number = data.aadhaar_number

        existing_doc = db.query(KYCDocument).filter(
            KYCDocument.customer_id == data.customer_id,
            KYCDocument.document_type == DocumentType.AADHAAR,
        ).first()
        if existing_doc:
            existing_doc.verification_status = VerificationStatus.VERIFIED
            existing_doc.verification_method = "aadhaar_otp"
            existing_doc.verified_at = datetime.utcnow()

        verification = KYCVerification(
            document_id=existing_doc.id if existing_doc else None,
            customer_id=data.customer_id,
            verification_type="aadhaar_otp",
            request_payload=json.dumps({"aadhaar": data.aadhaar_number[-4:]}),
            response_payload=json.dumps(result),
            is_successful=True,
            confidence_score=result.get("confidence", 1.0),
        )
        db.add(verification)
        db.commit()

    return result


@router.post("/pan/verify", response_model=dict)
def verify_pan(data: PANVerifyRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = kyc_processor.verify_pan(data.pan_number, data.full_name, data.date_of_birth)

    if result.get("valid"):
        customer.pan_number = data.pan_number.upper()

        existing_doc = db.query(KYCDocument).filter(
            KYCDocument.customer_id == data.customer_id,
            KYCDocument.document_type == DocumentType.PAN,
        ).first()
        if existing_doc:
            existing_doc.verification_status = VerificationStatus.VERIFIED
            existing_doc.verification_method = "pan_nsdl_api"
            existing_doc.verified_at = datetime.utcnow()
            existing_doc.document_number = data.pan_number.upper()

        db.commit()

    return result


@router.post("/document/{doc_id}/approve", response_model=KYCDocumentResponse)
def approve_document(doc_id: str, reviewed_by: str = "system", db: Session = Depends(get_db)):
    doc = db.query(KYCDocument).filter(KYCDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.verification_status = VerificationStatus.VERIFIED
    doc.verified_at = datetime.utcnow()
    doc.verified_by = reviewed_by
    db.commit()

    _check_and_complete_kyc(doc.customer_id, db)
    db.refresh(doc)
    return doc


@router.post("/document/{doc_id}/reject", response_model=KYCDocumentResponse)
def reject_document(doc_id: str, reason: str, reviewed_by: str = "system", db: Session = Depends(get_db)):
    doc = db.query(KYCDocument).filter(KYCDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.verification_status = VerificationStatus.REJECTED
    doc.verified_at = datetime.utcnow()
    doc.verified_by = reviewed_by
    doc.rejection_reason = reason
    db.commit()
    db.refresh(doc)
    return doc


def _check_and_complete_kyc(customer_id: str, db: Session):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return
    docs = db.query(KYCDocument).filter(KYCDocument.customer_id == customer_id).all()
    status = kyc_processor.compute_kyc_status(docs)
    if status["is_complete"]:
        customer.kyc_completed = True
        customer.kyc_completion_date = datetime.utcnow()
        customer.kyc_expiry_date = datetime.utcnow() + timedelta(days=settings.rekyc_validity_years * 365)
        customer.rekyc_due_date = customer.kyc_expiry_date
        db.commit()
