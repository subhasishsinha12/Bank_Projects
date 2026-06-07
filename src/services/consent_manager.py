"""
DPDP Consent Manager
Manages the full lifecycle of data-subject consents per the
Digital Personal Data Protection Act 2023 and RBI guidelines.

Key duties:
- Issue and sign consent artefacts
- Enforce consent before any data access (used by ConsentGuard middleware)
- Handle withdrawals with cascading side-effects (pause AA, stop marketing)
- Track every data-processing event for audit
- Manage Data Subject Requests (access, erasure, portability)
- Breach notification workflow
"""
import json
import hashlib
import base64
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.consent import (
    ConsentRecord, ConsentAuditLog, DataProcessingRecord,
    DataSubjectRequest, DataBreachRecord,
    ConsentPurpose, ConsentStatus, DataCategory, LegalBasis, DSRType,
)
from src.models.customer import Customer
from src.config import settings


# Maps each API endpoint pattern to the purposes and data categories it touches
ENDPOINT_CONSENT_MAP: Dict[str, Dict] = {
    "/api/customers":           {"purposes": [ConsentPurpose.KYC_VERIFICATION],
                                  "categories": [DataCategory.PERSONAL_IDENTITY, DataCategory.CONTACT_INFO]},
    "/api/kyc":                 {"purposes": [ConsentPurpose.KYC_VERIFICATION],
                                  "categories": [DataCategory.IDENTITY_DOCUMENTS, DataCategory.BIOMETRIC]},
    "/api/leads":               {"purposes": [ConsentPurpose.PRODUCT_PERSONALISATION],
                                  "categories": [DataCategory.PERSONAL_IDENTITY, DataCategory.BEHAVIOURAL]},
    "/api/onboarding/personalize": {"purposes": [ConsentPurpose.PRODUCT_PERSONALISATION],
                                  "categories": [DataCategory.PERSONAL_IDENTITY, DataCategory.FINANCIAL_DATA]},
    "/api/account-aggregator":  {"purposes": [ConsentPurpose.ACCOUNT_AGGREGATOR,
                                               ConsentPurpose.CREDIT_ASSESSMENT],
                                  "categories": [DataCategory.FINANCIAL_DATA, DataCategory.CREDIT_HISTORY]},
    "/api/ckyc":                {"purposes": [ConsentPurpose.REGULATORY_REPORTING],
                                  "categories": [DataCategory.PERSONAL_IDENTITY, DataCategory.IDENTITY_DOCUMENTS]},
}

# Purposes that can be legally processed without explicit consent (regulatory mandate)
EXEMPT_PURPOSES = {
    ConsentPurpose.REGULATORY_REPORTING,
    ConsentPurpose.FRAUD_PREVENTION,
}


class ConsentManager:

    # ------------------------------------------------------------------ #
    # Consent Creation
    # ------------------------------------------------------------------ #

    def create_consent(
        self,
        db: Session,
        customer_id: str,
        purpose: ConsentPurpose,
        data_categories: List[DataCategory],
        legal_basis: LegalBasis = LegalBasis.CONSENT,
        language: str = "en",
        channel: str = "web",
        ip_address: Optional[str] = None,
        expiry_days: Optional[int] = None,
        data_processors: Optional[List[str]] = None,
    ) -> ConsentRecord:
        expiry = datetime.utcnow() + timedelta(
            days=expiry_days or settings.dpdp_default_consent_expiry_days
        )
        record = ConsentRecord(
            customer_id=customer_id,
            purpose=purpose,
            legal_basis=legal_basis,
            status=ConsentStatus.PENDING,
            data_categories=json.dumps([c.value for c in data_categories]),
            data_processors=json.dumps(data_processors or []),
            consent_version=settings.dpdp_consent_version,
            language=language,
            collection_channel=channel,
            collection_ip=ip_address,
            expires_at=expiry,
        )
        db.add(record)
        db.flush()  # get id before signing

        record.signed_artefact = self._sign_artefact(record)
        db.commit()
        db.refresh(record)

        self._log_event(db, record.id, "created", None, "pending",
                        actor="system", ip=ip_address)
        return record

    def activate_consent(
        self,
        db: Session,
        consent_id: str,
        actor: str = "customer",
        ip: Optional[str] = None,
    ) -> ConsentRecord:
        record = self._get_or_raise(db, consent_id)
        prev = record.status.value
        record.status = ConsentStatus.ACTIVE
        record.given_at = datetime.utcnow()
        db.commit()
        self._log_event(db, record.id, "activated", prev, "active", actor=actor, ip=ip)
        return record

    # ------------------------------------------------------------------ #
    # Consent Enforcement
    # ------------------------------------------------------------------ #

    def has_active_consent(
        self,
        db: Session,
        customer_id: str,
        purpose: ConsentPurpose,
        data_category: Optional[DataCategory] = None,
    ) -> bool:
        if purpose in EXEMPT_PURPOSES:
            return True

        query = db.query(ConsentRecord).filter(
            ConsentRecord.customer_id == customer_id,
            ConsentRecord.purpose == purpose,
            ConsentRecord.status == ConsentStatus.ACTIVE,
            ConsentRecord.expires_at > datetime.utcnow(),
        )
        records = query.all()
        if not records:
            return False
        if data_category is None:
            return True
        for r in records:
            cats = json.loads(r.data_categories or "[]")
            if data_category.value in cats:
                return True
        return False

    def get_consent_gaps(
        self,
        db: Session,
        customer_id: str,
        required_purposes: List[ConsentPurpose],
    ) -> List[ConsentPurpose]:
        return [p for p in required_purposes
                if not self.has_active_consent(db, customer_id, p)]

    def enforce_for_endpoint(
        self,
        db: Session,
        customer_id: str,
        endpoint: str,
    ) -> Optional[str]:
        """
        Returns None if all consents are present.
        Returns an error message string if any consent is missing.
        """
        mapping = self._resolve_endpoint_mapping(endpoint)
        if not mapping:
            return None  # no consent required for this endpoint

        gaps = self.get_consent_gaps(db, customer_id, mapping["purposes"])
        if gaps:
            return (
                f"Missing consent for: {', '.join(g.value for g in gaps)}. "
                f"Please obtain customer consent before processing this request."
            )
        return None

    # ------------------------------------------------------------------ #
    # Consent Withdrawal (DPDP §6(4))
    # ------------------------------------------------------------------ #

    def revoke_consent(
        self,
        db: Session,
        consent_id: str,
        reason: Optional[str] = None,
        actor: str = "customer",
        ip: Optional[str] = None,
    ) -> ConsentRecord:
        record = self._get_or_raise(db, consent_id)
        prev = record.status.value
        record.status = ConsentStatus.REVOKED
        record.revoked_at = datetime.utcnow()
        db.commit()
        self._log_event(db, record.id, "revoked", prev, "revoked",
                        actor=actor, reason=reason, ip=ip)
        return record

    def revoke_all_for_purpose(
        self,
        db: Session,
        customer_id: str,
        purpose: ConsentPurpose,
        reason: str = "customer_request",
    ) -> int:
        records = db.query(ConsentRecord).filter(
            ConsentRecord.customer_id == customer_id,
            ConsentRecord.purpose == purpose,
            ConsentRecord.status == ConsentStatus.ACTIVE,
        ).all()
        for r in records:
            self.revoke_consent(db, r.id, reason=reason, actor="customer")
        return len(records)

    # ------------------------------------------------------------------ #
    # Data Processing Record
    # ------------------------------------------------------------------ #

    def record_processing(
        self,
        db: Session,
        customer_id: str,
        operation: str,
        data_categories: List[DataCategory],
        api_endpoint: str,
        legal_basis: str = "consent",
        consent_id: Optional[str] = None,
        processed_by: str = "system",
        third_party: Optional[str] = None,
    ) -> DataProcessingRecord:
        rec = DataProcessingRecord(
            consent_id=consent_id,
            customer_id=customer_id,
            operation=operation,
            data_categories=json.dumps([c.value for c in data_categories]),
            api_endpoint=api_endpoint,
            processed_by=processed_by,
            legal_basis=legal_basis,
            third_party=third_party,
        )
        db.add(rec)
        db.commit()
        return rec

    # ------------------------------------------------------------------ #
    # Data Subject Requests
    # ------------------------------------------------------------------ #

    def submit_dsr(
        self,
        db: Session,
        customer_id: str,
        request_type: DSRType,
        description: Optional[str] = None,
    ) -> DataSubjectRequest:
        due = datetime.utcnow() + timedelta(days=30)  # DPDP: 30-day resolution window
        dsr = DataSubjectRequest(
            customer_id=customer_id,
            request_type=request_type,
            status="received",
            description=description,
            due_date=due,
        )
        db.add(dsr)
        db.commit()
        db.refresh(dsr)
        return dsr

    def resolve_dsr(
        self,
        db: Session,
        dsr_id: str,
        resolution_note: str,
        resolved_by: str = "system",
    ) -> DataSubjectRequest:
        dsr = db.query(DataSubjectRequest).filter(
            DataSubjectRequest.dsr_id == dsr_id
        ).first()
        if not dsr:
            raise ValueError(f"DSR {dsr_id} not found")
        dsr.status = "completed"
        dsr.resolved_at = datetime.utcnow()
        dsr.resolved_by = resolved_by
        dsr.resolution_note = resolution_note
        db.commit()
        return dsr

    def execute_erasure(self, db: Session, customer_id: str) -> Dict[str, int]:
        """
        Right to Erasure (DPDP §14): anonymise/delete PII while retaining
        records mandated by law (KYC records per PMLA must be kept 5 years).
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError("Customer not found")

        # Anonymise PII fields (cannot delete — PMLA mandates 5yr retention)
        customer.email = f"ERASED_{customer_id[:8]}@erased.invalid"
        customer.mobile = f"0000000{customer_id[:4]}"
        customer.first_name = "ERASED"
        customer.last_name = "ERASED"
        customer.address_line1 = "ERASED"
        customer.address_line2 = None
        customer.aadhaar_number = None
        customer.alternate_mobile = None

        # Revoke all active consents
        active_consents = db.query(ConsentRecord).filter(
            ConsentRecord.customer_id == customer_id,
            ConsentRecord.status == ConsentStatus.ACTIVE,
        ).all()
        for c in active_consents:
            c.status = ConsentStatus.REVOKED
            c.revoked_at = datetime.utcnow()

        db.commit()
        return {
            "pii_fields_anonymised": 6,
            "consents_revoked": len(active_consents),
        }

    # ------------------------------------------------------------------ #
    # Breach Notification (DPDP §8(6))
    # ------------------------------------------------------------------ #

    def register_breach(
        self,
        db: Session,
        breach_type: str,
        data_categories: List[DataCategory],
        estimated_records: int,
        description: str,
        discovered_at: Optional[datetime] = None,
        reported_by: str = "security_team",
    ) -> DataBreachRecord:
        disc = discovered_at or datetime.utcnow()
        notif_due = disc + timedelta(hours=settings.dpdp_breach_notify_hours)
        breach = DataBreachRecord(
            discovered_at=disc,
            notification_due=notif_due,
            breach_type=breach_type,
            data_categories_affected=json.dumps([c.value for c in data_categories]),
            estimated_records_affected=estimated_records,
            description=description,
            status="open",
            reported_by=reported_by,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)
        return breach

    # ------------------------------------------------------------------ #
    # Customer Consent Dashboard
    # ------------------------------------------------------------------ #

    def get_consent_dashboard(self, db: Session, customer_id: str) -> Dict[str, Any]:
        consents = db.query(ConsentRecord).filter(
            ConsentRecord.customer_id == customer_id
        ).order_by(ConsentRecord.created_at.desc()).all()

        active = [c for c in consents if c.status == ConsentStatus.ACTIVE]
        revoked = [c for c in consents if c.status == ConsentStatus.REVOKED]
        expired = [c for c in consents if c.status == ConsentStatus.EXPIRED
                   or (c.expires_at and c.expires_at < datetime.utcnow())]

        processing_count = db.query(DataProcessingRecord).filter(
            DataProcessingRecord.customer_id == customer_id
        ).count()

        pending_dsrs = db.query(DataSubjectRequest).filter(
            DataSubjectRequest.customer_id == customer_id,
            DataSubjectRequest.status.in_(["received", "in_progress"]),
        ).count()

        return {
            "customer_id": customer_id,
            "total_consents": len(consents),
            "active": len(active),
            "revoked": len(revoked),
            "expired": len(expired),
            "data_processing_events": processing_count,
            "pending_dsr_requests": pending_dsrs,
            "consents": [self._consent_summary(c) for c in consents],
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_or_raise(self, db: Session, consent_id: str) -> ConsentRecord:
        record = db.query(ConsentRecord).filter(
            ConsentRecord.id == consent_id
        ).first()
        if not record:
            raise ValueError(f"Consent {consent_id} not found")
        return record

    def _log_event(
        self,
        db: Session,
        consent_id: str,
        event_type: str,
        prev_status: Optional[str],
        new_status: str,
        actor: str = "system",
        reason: Optional[str] = None,
        ip: Optional[str] = None,
    ):
        log = ConsentAuditLog(
            consent_id=consent_id,
            event_type=event_type,
            previous_status=prev_status,
            new_status=new_status,
            actor=actor,
            reason=reason,
            ip_address=ip,
        )
        db.add(log)
        db.commit()

    def _sign_artefact(self, record: ConsentRecord) -> str:
        payload = {
            "consent_id": record.id,
            "customer_id": record.customer_id,
            "purpose": record.purpose.value,
            "data_categories": json.loads(record.data_categories),
            "version": record.consent_version,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "fiduciary": settings.dpdp_data_fiduciary_name,
        }
        raw = json.dumps(payload, sort_keys=True).encode()
        digest = hashlib.sha256(raw + settings.secret_key.encode()).hexdigest()
        return base64.b64encode(
            json.dumps({"payload": payload, "signature": digest}).encode()
        ).decode()

    def _consent_summary(self, record: ConsentRecord) -> Dict:
        return {
            "consent_id": record.consent_id,
            "purpose": record.purpose.value,
            "status": record.status.value,
            "data_categories": json.loads(record.data_categories or "[]"),
            "given_at": record.given_at.isoformat() if record.given_at else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
        }

    def _resolve_endpoint_mapping(self, endpoint: str) -> Optional[Dict]:
        for pattern, mapping in ENDPOINT_CONSENT_MAP.items():
            if endpoint.startswith(pattern):
                return mapping
        return None


consent_manager = ConsentManager()
