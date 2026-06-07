"""Tests for KYC, Re-KYC, and CKYC APIs"""
import pytest
from fastapi.testclient import TestClient


import uuid as _uuid

@pytest.fixture
def sample_customer(client: TestClient):
    suffix = _uuid.uuid4().hex[:6]
    mobile = f"9{suffix[:9].zfill(9)}"
    response = client.post("/api/customers/", json={
        "first_name": "Vikram",
        "last_name": "Malhotra",
        "mobile": mobile,
        "email": f"vikram_{suffix}@example.com",
        "pan_number": f"ABCDE{suffix[:4].upper()}F",
        "source": "test",
    })
    assert response.status_code == 201
    return response.json()


def test_create_customer(client: TestClient):
    response = client.post("/api/customers/", json={
        "first_name": "Ananya",
        "last_name": "Singh",
        "mobile": "9011223344",
        "email": "ananya@example.com",
        "annual_income": 800000,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"].startswith("CUST")
    assert data["segment"] == "mass_affluent"


def test_kyc_status_no_docs(client: TestClient, sample_customer):
    cid = sample_customer["id"]
    response = client.get(f"/api/kyc/customer/{cid}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["kyc_completed"] is False
    assert data["documents_submitted"] == 0


def test_aadhaar_otp_flow(client: TestClient, sample_customer):
    cid = sample_customer["id"]
    otp_resp = client.post("/api/kyc/aadhaar/send-otp", json={
        "customer_id": cid,
        "aadhaar_number": "123456789012",
    })
    assert otp_resp.status_code == 200
    data = otp_resp.json()
    assert data["success"] is True
    assert "transaction_id" in data

    txn_id = data["transaction_id"]
    verify_resp = client.post("/api/kyc/aadhaar/verify-otp", json={
        "customer_id": cid,
        "aadhaar_number": "123456789012",
        "otp": "123456",
        "transaction_id": txn_id,
    })
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True


def test_pan_verification(client: TestClient, sample_customer):
    cid = sample_customer["id"]
    response = client.post("/api/kyc/pan/verify", json={
        "customer_id": cid,
        "pan_number": "ABCDE1234F",
        "full_name": "Vikram Malhotra",
        "date_of_birth": "01/01/1990",
    })
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_ckyc_search_by_pan(client: TestClient):
    response = client.post("/api/ckyc/search", json={"pan_number": "ABCDE1234F"})
    assert response.status_code == 200
    data = response.json()
    assert "found" in data
    assert "ckyc_id" in data


def test_ckyc_search_missing_params(client: TestClient):
    response = client.post("/api/ckyc/search", json={})
    assert response.status_code == 400


def test_ckyc_register_without_kyc(client: TestClient, sample_customer):
    cid = sample_customer["id"]
    response = client.post(f"/api/ckyc/register/{cid}")
    assert response.status_code == 400  # KYC not complete


def test_rekyc_initiate(client: TestClient, sample_customer):
    cid = sample_customer["id"]
    response = client.post("/api/rekyc/initiate", json={
        "customer_id": cid,
        "trigger_reason": "periodic",
        "preferred_channel": "email",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == cid
    assert data["status"] == "initiated"


def test_rekyc_duplicate_request(client: TestClient, sample_customer):
    cid = sample_customer["id"]
    client.post("/api/rekyc/initiate", json={"customer_id": cid, "trigger_reason": "test"})
    response = client.post("/api/rekyc/initiate", json={"customer_id": cid})
    assert response.status_code == 409


def test_rekyc_analytics(client: TestClient):
    response = client.get("/api/rekyc/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_customers_with_kyc" in data
    assert "rekyc_overdue" in data


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
