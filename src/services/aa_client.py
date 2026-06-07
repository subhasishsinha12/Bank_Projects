"""
Account Aggregator Client — Sahamati / ReBIT AA Spec v2.0
Implements the Financial Information User (FIU) side.

Full spec: https://api.rebit.org.in/
Sahamati sandbox: https://api.sandbox.sahamati.org.in

Flow:
  1. POST /Consent              → create consent request, get consentHandle + redirect URL
  2. Customer approves via AA app (Finvu / OneMoney / PhonePe)
  3. POST /Consent/handle/fetch → poll until status = ACTIVE, get consentId
  4. POST /FI/request           → create data-fetch session, get sessionId
  5. GET  /FI/fetch/{sessionId} → retrieve encrypted financial data
  6. Decrypt JWE → parse → compute FinancialSummary
"""
import json
import uuid
import hashlib
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from src.config import settings
from src.models.account_aggregator import FIType, FetchType


# ReBIT purpose codes
PURPOSE_CODES = {
    "credit_assessment":  {"code": "101", "text": "Credit Underwriting / Assessment"},
    "kyc_verification":   {"code": "103", "text": "Customer Identification / KYC"},
    "wealth_management":  {"code": "104", "text": "Wealth Management"},
    "onboarding":         {"code": "101", "text": "Account Opening / Onboarding"},
}

# Known AA providers and their redirect URL templates
AA_PROVIDERS = {
    "finvu":    "https://finvu.in/webApp/consent?handle={handle}",
    "onemoney": "https://onemoney.in/consent?handle={handle}",
    "phonepe":  "https://phonepe.com/aa/consent?handle={handle}",
    "cams":     "https://camsfinserv.com/aa/consent?handle={handle}",
}


class AAClient:

    def __init__(self):
        self.base_url = settings.aa_base_url
        self.fiu_id   = settings.aa_fiu_id
        self._token   = None
        self._token_expiry = None

    # ------------------------------------------------------------------ #
    # Auth
    # ------------------------------------------------------------------ #

    def _get_token(self) -> str:
        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._token
        if not settings.aa_client_id:
            return "sandbox-mock-token"
        try:
            resp = httpx.post(
                f"{self.base_url}/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.aa_client_id,
                    "client_secret": settings.aa_client_secret,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)
            return self._token
        except Exception:
            return "sandbox-mock-token"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "x-jws-signature": "mock-signature",   # In production: JWS-signed header
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _txn_id(self) -> str:
        return str(uuid.uuid4())

    # ------------------------------------------------------------------ #
    # Step 1: Create Consent Request
    # ------------------------------------------------------------------ #

    def create_consent_request(
        self,
        customer_mobile: str,
        customer_aa_handle: str,         # e.g. customer@finvu
        fi_types: List[FIType],
        purpose: str = "credit_assessment",
        fetch_type: FetchType = FetchType.ONE_TIME,
        data_date_range_months: int = 6,
        aa_provider: str = "finvu",
    ) -> Dict[str, Any]:
        """
        POST /Consent
        Creates a consent artefact request. Customer must approve via their AA app.
        Returns consentHandle and redirect_url.
        """
        now = datetime.utcnow()
        data_from = now - timedelta(days=data_date_range_months * 30)
        consent_expiry = now + timedelta(days=365)

        purpose_info = PURPOSE_CODES.get(purpose, PURPOSE_CODES["credit_assessment"])
        txn = self._txn_id()

        consent_detail = {
            "consentStart": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "consentExpiry": consent_expiry.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "consentMode": "STORE",
            "fetchType": fetch_type.value,
            "consentTypes": ["TRANSACTIONS", "SUMMARY", "PROFILE"],
            "fiTypes": [fi.value for fi in fi_types],
            "DataConsumer": {"id": self.fiu_id},
            "Customer": {"id": customer_aa_handle},
            "FIPResourceList": [],           # empty = let AA discover
            "DataLife": {"unit": "MONTH", "value": 6},
            "Frequency": {"unit": "MONTH", "value": 1},
            "DataFilter": [
                {
                    "type": "TRANSACTIONAMOUNT",
                    "operator": ">=",
                    "value": "0",
                }
            ],
            "Purpose": {
                "code": purpose_info["code"],
                "refUri": "https://api.rebit.org.in/aa/purpose",
                "text": purpose_info["text"],
                "Category": {"type": "Personal Finance"},
            },
            "DataDateTimeRange": {
                "from": data_from.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "to": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
        }

        if not settings.aa_client_id:
            return self._mock_consent_response(txn, customer_aa_handle, aa_provider)

        try:
            payload = {
                "ver": "2.0.0",
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "txnid": txn,
                "ConsentDetail": consent_detail,
            }
            resp = httpx.post(
                f"{self.base_url}/Consent",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            handle = data.get("ConsentHandle", txn)
            redirect = AA_PROVIDERS.get(aa_provider, AA_PROVIDERS["finvu"]).format(handle=handle)
            return {
                "success": True,
                "txn_id": txn,
                "consent_handle": handle,
                "redirect_url": redirect,
                "status": "PENDING",
                "message": "Customer must approve consent in their AA app",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------ #
    # Step 2: Poll Consent Status (webhook preferred in production)
    # ------------------------------------------------------------------ #

    def get_consent_status(self, consent_handle: str) -> Dict[str, Any]:
        """GET /Consent/handle/{consentHandle} — poll until status = ACTIVE"""
        if not settings.aa_client_id:
            return self._mock_consent_status(consent_handle)
        try:
            resp = httpx.get(
                f"{self.base_url}/Consent/handle/{consent_handle}",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("ConsentStatus"),
                "consent_id": data.get("consentId"),
                "signed_consent": data.get("signedConsent"),
            }
        except Exception as e:
            return {"status": "PENDING", "error": str(e)}

    # ------------------------------------------------------------------ #
    # Step 3: Request Data Fetch
    # ------------------------------------------------------------------ #

    def request_fi_data(
        self,
        consent_id: str,
        signed_consent: str,
        fi_types: List[FIType],
        data_from: datetime,
        data_to: datetime,
    ) -> Dict[str, Any]:
        """POST /FI/request — initiate data fetch session"""
        if not settings.aa_client_id:
            return self._mock_fi_request()

        txn = self._txn_id()
        payload = {
            "ver": "2.0.0",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "txnid": txn,
            "FIDataRange": {
                "from": data_from.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "to":   data_to.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
            "Consent": {
                "id": consent_id,
                "digitalSignature": signed_consent,
            },
            "KeyMaterial": self._generate_key_material(),
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/FI/request",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "session_id": data.get("sessionId"),
                "txn_id": txn,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------ #
    # Step 4: Fetch Financial Data
    # ------------------------------------------------------------------ #

    def fetch_fi_data(self, session_id: str, consent_id: str) -> Dict[str, Any]:
        """POST /FI/fetch/{sessionId} — retrieve encrypted financial data"""
        if not settings.aa_client_id:
            return self._mock_fi_fetch(session_id)
        try:
            payload = {
                "ver": "2.0.0",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "txnid": self._txn_id(),
                "sessionId": session_id,
                "Consent": {"id": consent_id},
                "fipId": "ALL",
            }
            resp = httpx.post(
                f"{self.base_url}/FI/fetch/{session_id}",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def decrypt_fi_data(self, encrypted_payload: Dict) -> List[Dict]:
        """
        Decrypt JWE-encrypted FI data using FIU's private key.
        In production: use python-jose or cryptography library with your RSA key.
        Returns list of account data objects per ReBIT schema.
        """
        # Stub: in production perform ECDH-ES+A256GCM decryption
        return encrypted_payload.get("FI", [])

    # ------------------------------------------------------------------ #
    # Mock responses (no AA credentials configured)
    # ------------------------------------------------------------------ #

    def _mock_consent_response(self, txn: str, aa_handle: str, provider: str) -> Dict:
        handle = f"HANDLE-{hashlib.sha256(aa_handle.encode()).hexdigest()[:12].upper()}"
        return {
            "success": True,
            "txn_id": txn,
            "consent_handle": handle,
            "redirect_url": AA_PROVIDERS.get(provider, AA_PROVIDERS["finvu"]).format(handle=handle),
            "status": "PENDING",
            "message": "[SANDBOX] Consent created. Customer must approve in AA app.",
            "sandbox": True,
        }

    def _mock_consent_status(self, handle: str) -> Dict:
        consent_id = f"CONSENT-{hashlib.sha256(handle.encode()).hexdigest()[:16].upper()}"
        return {
            "status": "ACTIVE",
            "consent_id": consent_id,
            "signed_consent": f"mock-signed-consent-{consent_id}",
            "sandbox": True,
        }

    def _mock_fi_request(self) -> Dict:
        session_id = f"SESSION-{str(uuid.uuid4())[:12].upper()}"
        return {"success": True, "session_id": session_id, "txn_id": self._txn_id(), "sandbox": True}

    def _mock_fi_fetch(self, session_id: str) -> Dict:
        """Realistic mock bank statement data (6 months, 2 accounts)."""
        return {
            "status": "COMPLETED",
            "FI": [
                {
                    "fipID": "HDFC-FIP",
                    "data": [
                        {
                            "linkRefNumber": "XXXX4321",
                            "maskedAccNumber": "XXXX4321",
                            "Profile": {
                                "Holders": {"Holder": [{
                                    "name": "Sample Customer",
                                    "dob": "1990-01-01",
                                    "mobile": "98XXXXXXXX",
                                    "pan": "ABCDE1234F",
                                }]},
                            },
                            "Summary": {
                                "currentBalance": "125000.00",
                                "currency": "INR",
                                "exchgeRate": "",
                                "balanceDateTime": datetime.utcnow().isoformat(),
                                "type": "SAVINGS",
                                "branch": "Mumbai Main",
                                "facility": "OD",
                                "ifscCode": "HDFC0000001",
                                "micrCode": "400240001",
                                "openingDate": "2018-04-01",
                                "currentODLimit": "0",
                                "drawingLimit": "0",
                                "status": "ACTIVE",
                                "Pending": {"amount": "0", "transactionType": "DEBIT"},
                            },
                            "Transactions": {
                                "Transaction": self._mock_transactions(),
                            },
                        }
                    ],
                },
                {
                    "fipID": "ICICI-FIP",
                    "data": [
                        {
                            "linkRefNumber": "XXXX8765",
                            "maskedAccNumber": "XXXX8765",
                            "Profile": {"Holders": {"Holder": [{"name": "Sample Customer"}]}},
                            "Summary": {
                                "currentBalance": "43200.00",
                                "currency": "INR",
                                "type": "SAVINGS",
                                "status": "ACTIVE",
                            },
                            "Transactions": {
                                "Transaction": self._mock_transactions(salary=55000, employer="ABC Corp"),
                            },
                        }
                    ],
                },
            ],
            "sandbox": True,
        }

    def _mock_transactions(self, salary: float = 75000, employer: str = "XYZ Pvt Ltd") -> List[Dict]:
        txns = []
        now = datetime.utcnow()
        for i in range(6):
            month = now - timedelta(days=i * 30)
            # Salary credit
            txns.append({
                "type": "CREDIT",
                "mode": "NEFT",
                "amount": str(salary),
                "currentBalance": str(100000 + salary - (i * 5000)),
                "transactionTimestamp": month.replace(day=1).strftime("%Y-%m-%dT10:00:00.000Z"),
                "valueDate": month.replace(day=1).strftime("%Y-%m-%d"),
                "txnId": str(uuid.uuid4()),
                "narration": f"SALARY {employer} {month.strftime('%b%Y')}",
                "reference": f"SAL{month.strftime('%Y%m')}",
            })
            # EMI outflow
            txns.append({
                "type": "DEBIT",
                "mode": "ECS",
                "amount": "18500",
                "currentBalance": str(80000 - (i * 5000)),
                "transactionTimestamp": month.replace(day=5).strftime("%Y-%m-%dT09:00:00.000Z"),
                "valueDate": month.replace(day=5).strftime("%Y-%m-%d"),
                "txnId": str(uuid.uuid4()),
                "narration": "EMI HOME LOAN HDFC",
                "reference": f"EMI{month.strftime('%Y%m')}",
            })
            # Rent
            txns.append({
                "type": "DEBIT",
                "mode": "NEFT",
                "amount": "20000",
                "currentBalance": str(60000 - (i * 5000)),
                "transactionTimestamp": month.replace(day=3).strftime("%Y-%m-%dT11:00:00.000Z"),
                "valueDate": month.replace(day=3).strftime("%Y-%m-%d"),
                "txnId": str(uuid.uuid4()),
                "narration": "RENT PAYMENT",
                "reference": f"RENT{month.strftime('%Y%m')}",
            })
        return txns

    def _generate_key_material(self) -> Dict:
        """ECDH key material for JWE encryption. Stub for sandbox."""
        return {
            "cryptoAlg": "ECDH-ES+A256GCM",
            "curve": "Curve25519",
            "params": "mock-key-params",
            "DHPublicKey": {
                "expiry": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                "Parameters": "mock-dh-params",
                "KeyValue": "mock-public-key",
            },
            "Nonce": str(uuid.uuid4()),
        }


aa_client = AAClient()
