"""Tests for DPDP Consent Management"""
import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def customer(client: TestClient):
    uid = uuid.uuid4().hex[:8]
    r = client.post("/api/customers/", json={
        "first_name": "Meena", "last_name": "Iyer",
        "mobile": f"8{uid[:9]}",
        "email": f"meena_{uid}@test.com",
    })
    assert r.status_code == 201
    return r.json()


def test_request_consent(client: TestClient, customer):
    r = client.post("/api/consent/request", json={
        "customer_id": customer["id"],
        "purpose": "kyc_verification",
        "data_categories": ["personal_identity", "identity_documents"],
        "legal_basis": "consent",
        "language": "en",
        "channel": "web",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["purpose"] == "kyc_verification"
    assert data["consent_id"].startswith("CONSENT-")
    return data


def test_activate_consent(client: TestClient, customer):
    # Create
    cr = client.post("/api/consent/request", json={
        "customer_id": customer["id"],
        "purpose": "product_personalisation",
        "data_categories": ["personal_identity", "behavioural"],
    })
    assert cr.status_code == 201
    consent_id = cr.json()["id"]

    # Activate
    ar = client.post("/api/consent/activate", json={
        "consent_id": consent_id, "actor": "customer"
    })
    assert ar.status_code == 200
    assert ar.json()["status"] == "active"


def test_idempotent_consent_request(client: TestClient, customer):
    """Requesting the same active consent twice should return the existing one."""
    payload = {
        "customer_id": customer["id"],
        "purpose": "fraud_prevention",
        "data_categories": ["device_data"],
    }
    r1 = client.post("/api/consent/request", json=payload)
    assert r1.status_code == 201
    cid = r1.json()["id"]
    client.post("/api/consent/activate", json={"consent_id": cid})

    r2 = client.post("/api/consent/request", json=payload)
    assert r2.status_code == 201
    assert r2.json()["id"] == cid   # same record returned


def test_revoke_consent(client: TestClient, customer):
    cr = client.post("/api/consent/request", json={
        "customer_id": customer["id"],
        "purpose": "marketing_communication",
        "data_categories": ["contact_info"],
    })
    cid = cr.json()["id"]
    client.post("/api/consent/activate", json={"consent_id": cid})

    rr = client.post("/api/consent/revoke", json={
        "consent_id": cid, "reason": "customer_preference"
    })
    assert rr.status_code == 200
    assert rr.json()["status"] == "revoked"


def test_consent_bundle(client: TestClient, customer):
    r = client.post(f"/api/consent/bundle/{customer['id']}?language=en&channel=web")
    assert r.status_code == 200
    data = r.json()
    assert data["consents_created"] == 3
    purposes = {c["purpose"] for c in data["bundle"]}
    assert "kyc_verification" in purposes
    assert "product_personalisation" in purposes
    assert "fraud_prevention" in purposes


def test_consent_dashboard(client: TestClient, customer):
    # Create a consent first
    cr = client.post("/api/consent/request", json={
        "customer_id": customer["id"],
        "purpose": "analytics",
        "data_categories": ["behavioural"],
    })
    client.post("/api/consent/activate", json={"consent_id": cr.json()["id"]})

    r = client.get(f"/api/consent/customer/{customer['id']}")
    assert r.status_code == 200
    data = r.json()
    assert "total_consents" in data
    assert "active" in data
    assert isinstance(data["consents"], list)


def test_check_consent_has_active(client: TestClient, customer):
    cr = client.post("/api/consent/request", json={
        "customer_id": customer["id"],
        "purpose": "credit_assessment",
        "data_categories": ["financial_data"],
    })
    cid = cr.json()["id"]
    client.post("/api/consent/activate", json={"consent_id": cid})

    r = client.get(f"/api/consent/customer/{customer['id']}/check?purpose=credit_assessment")
    assert r.status_code == 200
    assert r.json()["has_consent"] is True


def test_check_consent_missing(client: TestClient, customer):
    r = client.get(f"/api/consent/customer/{customer['id']}/check?purpose=third_party_sharing")
    assert r.status_code == 200
    assert r.json()["has_consent"] is False
    assert r.json()["obtain_url"] is not None


def test_submit_dsr_access(client: TestClient, customer):
    r = client.post("/api/consent/dsr", json={
        "customer_id": customer["id"],
        "request_type": "access",
        "description": "I want to know what data you hold about me.",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["dsr_id"].startswith("DSR-")
    assert data["status"] == "received"
    assert data["due_date"] is not None


def test_dsr_erasure_and_resolve(client: TestClient, customer):
    dr = client.post("/api/consent/dsr", json={
        "customer_id": customer["id"],
        "request_type": "erasure",
    })
    dsr_id = dr.json()["dsr_id"]

    rr = client.post(f"/api/consent/dsr/{dsr_id}/resolve",
                     params={"resolution_note": "Data anonymised.", "resolved_by": "dpo"})
    assert rr.status_code == 200
    assert rr.json()["status"] == "completed"


def test_register_breach(client: TestClient):
    r = client.post("/api/consent/breach", json={
        "breach_type": "unauthorized_access",
        "data_categories_affected": ["personal_identity", "contact_info"],
        "estimated_records_affected": 150,
        "description": "Unauthorized API access detected in audit log.",
        "reported_by": "soc_team",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["breach_ref"].startswith("BREACH-")
    assert data["notification_due"] is not None   # 72-hour deadline set
    assert data["status"] == "open"


def test_right_to_erasure(client: TestClient, customer):
    r = client.delete(f"/api/consent/customer/{customer['id']}/erase")
    assert r.status_code == 200
    data = r.json()
    assert data["pii_fields_anonymised"] == 6
    assert "PMLA" in data["legal_retention_note"]


def test_compliance_health(client: TestClient):
    r = client.get("/api/consent/compliance/health")
    assert r.status_code == 200
    data = r.json()
    assert "overall_status" in data
    assert "active_consents" in data
    assert "overdue_dsrs" in data
    assert data["dpdp_compliance_version"] == "1.0"


def test_processing_log(client: TestClient, customer):
    r = client.get(f"/api/consent/processing-log/{customer['id']}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
