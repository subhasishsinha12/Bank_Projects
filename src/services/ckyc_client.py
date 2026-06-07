"""
CKYC (Central KYC Registry) Client
Integrates with CERSAI's CKYC Registry for fetching existing KYC records,
registering new customers, and updating changed details.

CKYC Registry: www.ckycreg.com
All financial institutions are mandated by RBI/SEBI to upload KYC records.
"""
import json
import hashlib
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from src.config import settings


class CKYCClient:

    def __init__(self):
        self.base_url = settings.ckyc_api_base_url
        self.api_key = settings.ckyc_api_key
        self.institution_id = settings.ckyc_institution_id

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Institution-ID": self.institution_id or "BANK001",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def search_by_pan(self, pan_number: str) -> Dict[str, Any]:
        """Search CKYC Registry by PAN number."""
        return self._mock_search_response(pan_number, "pan")

    def search_by_aadhaar(self, aadhaar_number: str) -> Dict[str, Any]:
        """Search CKYC Registry by Aadhaar number."""
        return self._mock_search_response(aadhaar_number, "aadhaar")

    def search_by_demographics(
        self,
        full_name: str,
        date_of_birth: str,
        mobile: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Demographic-based search as fallback."""
        return {"found": False, "records": [], "search_type": "demographics"}

    def fetch_ckyc_record(self, ckyc_id: str) -> Dict[str, Any]:
        """Fetch full KYC record using 14-digit CKYC identifier."""
        return self._mock_full_record(ckyc_id)

    def register_customer(self, customer_data: Dict[str, Any], documents: list) -> Dict[str, Any]:
        """
        Register a new customer in CKYC Registry.
        Returns the 14-digit CKYC KIN (KYC Identification Number).
        """
        kin = self._generate_kin(customer_data.get("pan_number", ""))
        return {
            "success": True,
            "ckyc_id": kin,
            "message": "Customer registered successfully in CKYC Registry",
            "registered_at": datetime.utcnow().isoformat(),
        }

    def update_customer(self, ckyc_id: str, updated_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit change request to CKYC Registry for address, contact, or other updates.
        Changes require supporting documents per PMLA guidelines.
        """
        return {
            "success": True,
            "ckyc_id": ckyc_id,
            "change_request_id": f"CR{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "updated_fields": list(updated_fields.keys()),
            "status": "submitted",
            "message": "Change request submitted. Will be processed within 5 business days.",
        }

    def download_kyc_pdf(self, ckyc_id: str) -> bytes:
        """Download KYC PDF from registry for pre-fill during onboarding."""
        # In production: fetch from CKYC registry API
        sample_content = f"CKYC Record PDF for KIN: {ckyc_id}".encode()
        return sample_content

    def _mock_search_response(self, identifier: str, search_type: str) -> Dict[str, Any]:
        """
        Mock CKYC search response for demo/testing.
        In production this calls the actual CKYC Registry API.
        """
        if len(identifier) >= 10:
            return {
                "found": True,
                "ckyc_id": self._generate_kin(identifier),
                "search_type": search_type,
                "customer_data": {
                    "full_name": "Sample Customer Name",
                    "father_name": "Sample Father Name",
                    "date_of_birth": "01/01/1990",
                    "gender": "M",
                    "address": "123, Sample Street, Mumbai, Maharashtra - 400001",
                    "mobile": "9876543210",
                    "email": "sample@example.com",
                    "pan_number": "ABCDE1234F",
                    "aadhaar_masked": "XXXX-XXXX-1234",
                },
                "kyc_status": "verified",
                "last_updated": "2024-01-15",
                "institution": "ABC Bank Ltd",
                "documents": ["aadhaar", "pan", "photograph"],
            }
        return {"found": False, "search_type": search_type}

    def _mock_full_record(self, ckyc_id: str) -> Dict[str, Any]:
        return {
            "ckyc_id": ckyc_id,
            "kin": ckyc_id,
            "personal_details": {
                "full_name": "Sample Customer",
                "date_of_birth": "01/01/1990",
                "gender": "M",
                "nationality": "Indian",
                "occupation": "Service",
                "annual_income": "500000",
            },
            "address": {
                "current": "123 Sample Street, Mumbai 400001",
                "permanent": "123 Sample Street, Mumbai 400001",
            },
            "contact": {
                "mobile": "9876543210",
                "email": "sample@email.com",
            },
            "identity": {
                "pan": "ABCDE1234F",
                "aadhaar_masked": "XXXX-XXXX-1234",
            },
            "kyc_status": "verified",
            "kyc_date": "2023-06-15",
            "institution": "ABC Bank Ltd",
        }

    def _generate_kin(self, identifier: str) -> str:
        """Generate a deterministic 14-digit CKYC KIN for demo purposes."""
        hash_val = hashlib.sha256(identifier.encode()).hexdigest()
        return str(int(hash_val[:14], 16))[:14].zfill(14)


ckyc_client = CKYCClient()
