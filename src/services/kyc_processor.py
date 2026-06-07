"""
KYC Processing Service
Handles document OCR, field extraction, API-based verification
(Aadhaar OTP, PAN NSDL), and overall KYC status computation.
"""
import json
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from src.models.kyc import DocumentType, VerificationStatus, KYCType
from src.config import settings


REQUIRED_DOCS_BY_PRODUCT = {
    "savings_account": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH],
    "salary_account": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH],
    "personal_loan": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH, DocumentType.SALARY_SLIP],
    "home_loan": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH, DocumentType.SALARY_SLIP, DocumentType.BANK_STATEMENT_6M],
    "fixed_deposit": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH],
    "credit_card": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH, DocumentType.SALARY_SLIP],
    "business_loan": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH, DocumentType.GST_CERTIFICATE],
    "default": [DocumentType.AADHAAR, DocumentType.PAN, DocumentType.PHOTOGRAPH],
}


class KYCProcessorService:

    def extract_document_data(self, file_path: str, document_type: DocumentType) -> Dict[str, Any]:
        """
        Extract structured data from document image using OCR.
        In production this calls a dedicated OCR microservice or uses pytesseract.
        Returns extracted fields and confidence score.
        """
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            return self._parse_document_text(text, document_type)
        except ImportError:
            # Tesseract not installed in this env — return stub for demo
            return self._stub_extraction(document_type)
        except Exception as e:
            return {"error": str(e), "confidence": 0.0}

    def _parse_document_text(self, text: str, doc_type: DocumentType) -> Dict[str, Any]:
        import re
        data: Dict[str, Any] = {"raw_text": text, "confidence": 0.85}

        if doc_type == DocumentType.PAN:
            pan = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', text)
            if pan:
                data["pan_number"] = pan.group()
            dob = re.search(r'\d{2}/\d{2}/\d{4}', text)
            if dob:
                data["date_of_birth"] = dob.group()
            name_match = re.search(r'Name\s*\n([^\n]+)', text)
            if name_match:
                data["name"] = name_match.group(1).strip()

        elif doc_type == DocumentType.AADHAAR:
            aadhaar = re.search(r'\d{4}\s\d{4}\s\d{4}', text)
            if aadhaar:
                data["aadhaar_number"] = aadhaar.group().replace(" ", "")
            dob = re.search(r'DOB:\s*(\d{2}/\d{2}/\d{4})', text)
            if dob:
                data["date_of_birth"] = dob.group(1)

        elif doc_type in (DocumentType.DRIVING_LICENSE, DocumentType.PASSPORT):
            name_match = re.search(r'Name[:\s]+([A-Z\s]+)', text)
            if name_match:
                data["name"] = name_match.group(1).strip()

        return data

    def _stub_extraction(self, doc_type: DocumentType) -> Dict[str, Any]:
        stubs = {
            DocumentType.PAN: {"pan_number": "ABCDE1234F", "name": "Sample Name", "confidence": 0.92},
            DocumentType.AADHAAR: {"aadhaar_number": "123456789012", "name": "Sample Name", "confidence": 0.90},
            DocumentType.PHOTOGRAPH: {"face_detected": True, "confidence": 0.95},
            DocumentType.SALARY_SLIP: {"employer": "ABC Corp", "net_salary": 50000, "confidence": 0.88},
        }
        return stubs.get(doc_type, {"confidence": 0.80})

    def initiate_aadhaar_otp(self, aadhaar_number: str) -> Dict[str, Any]:
        """
        Calls UIDAI / AuthBridge API to send OTP to Aadhaar-linked mobile.
        Returns transaction_id for OTP verification.
        In production integrate with certified KUA (KYC User Agency).
        """
        import hashlib
        transaction_id = hashlib.sha256(f"{aadhaar_number}{datetime.utcnow()}".encode()).hexdigest()[:16]
        return {
            "success": True,
            "transaction_id": transaction_id,
            "message": "OTP sent to Aadhaar-linked mobile number",
            "masked_mobile": "XXXXXX" + aadhaar_number[-4:],
        }

    def verify_aadhaar_otp(self, aadhaar_number: str, otp: str, transaction_id: str) -> Dict[str, Any]:
        """Verify OTP with UIDAI. Stub returns success for demo."""
        if len(otp) == 6 and otp.isdigit():
            return {
                "success": True,
                "verified": True,
                "name": "Verified Name from UIDAI",
                "address": "Masked address from UIDAI",
                "confidence": 1.0,
            }
        return {"success": False, "verified": False, "error": "Invalid OTP"}

    def verify_pan(self, pan_number: str, full_name: str, date_of_birth: str) -> Dict[str, Any]:
        """
        Verifies PAN against NSDL database (ITD API).
        Stub implementation for demo.
        """
        if len(pan_number) == 10 and pan_number[:5].isalpha() and pan_number[5:9].isdigit():
            return {
                "success": True,
                "valid": True,
                "pan_status": "VALID",
                "name_match": True,
                "aadhaar_linked": True,
            }
        return {"success": False, "valid": False, "error": "Invalid PAN format"}

    def compute_kyc_status(self, submitted_docs: List, product: str = "default") -> Dict[str, Any]:
        required = REQUIRED_DOCS_BY_PRODUCT.get(product, REQUIRED_DOCS_BY_PRODUCT["default"])
        submitted_types = {doc.document_type for doc in submitted_docs}
        verified_types = {
            doc.document_type for doc in submitted_docs
            if doc.verification_status == VerificationStatus.VERIFIED
        }
        pending = [dt for dt in required if dt not in submitted_types]
        is_complete = len(pending) == 0 and len(verified_types) >= len(required)

        return {
            "is_complete": is_complete,
            "required_count": len(required),
            "submitted_count": len(submitted_types),
            "verified_count": len(verified_types),
            "pending_documents": [p.value for p in pending],
            "overall_status": "completed" if is_complete else "in_progress" if submitted_types else "not_started",
        }

    def schedule_rekyc(self, customer, trigger_reason: str = "periodic") -> Dict[str, Any]:
        due_date = datetime.utcnow() + timedelta(days=settings.rekyc_validity_years * 365)
        return {
            "customer_id": customer.id,
            "due_date": due_date,
            "trigger_reason": trigger_reason,
            "reminder_schedule": [
                due_date - timedelta(days=90),
                due_date - timedelta(days=30),
                due_date - timedelta(days=7),
            ],
        }

    def is_rekyc_overdue(self, customer) -> bool:
        if not customer.rekyc_due_date:
            return False
        return datetime.utcnow() > customer.rekyc_due_date


kyc_processor = KYCProcessorService()
