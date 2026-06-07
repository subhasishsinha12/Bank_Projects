"""Tests for Lead Management APIs"""
import pytest
from fastapi.testclient import TestClient


def test_create_lead(client: TestClient):
    response = client.post("/api/leads/", json={
        "name": "Rajesh Kumar",
        "email": "rajesh@example.com",
        "mobile": "9876543210",
        "city": "Mumbai",
        "state": "Maharashtra",
        "source": "website",
        "interested_product": "personal_loan",
        "interested_amount": 500000,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Rajesh Kumar"
    assert data["lead_score"] >= 0
    assert data["quality"] in ("hot", "warm", "cold")
    assert data["lead_id"].startswith("LEAD")


def test_list_leads(client: TestClient):
    response = client.get("/api/leads/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_filter_leads_by_quality(client: TestClient):
    response = client.get("/api/leads/?quality=cold")
    assert response.status_code == 200


def test_rescore_lead(client: TestClient):
    create_resp = client.post("/api/leads/", json={
        "name": "Priya Sharma",
        "mobile": "9123456780",
        "source": "referral",
    })
    assert create_resp.status_code == 201
    lead_id = create_resp.json()["lead_id"]

    rescore_resp = client.post(f"/api/leads/{lead_id}/rescore", json={
        "lead_id": lead_id,
        "additional_signals": {
            "annual_income": 1200000,
            "employment_type": "salaried",
            "credit_score": 760,
        },
    })
    assert rescore_resp.status_code == 200
    data = rescore_resp.json()
    assert "new_score" in data
    assert data["new_score"] >= 0


def test_log_activity(client: TestClient):
    create_resp = client.post("/api/leads/", json={
        "name": "Amit Verma",
        "mobile": "9000000001",
        "source": "digital_campaign",
    })
    lead_id = create_resp.json()["lead_id"]

    activity_resp = client.post(f"/api/leads/{lead_id}/activity", json={
        "lead_id": lead_id,
        "activity_type": "email_opened",
        "channel": "email",
        "performed_by": "system",
    })
    assert activity_resp.status_code == 200
    assert activity_resp.json()["score_impact"] == 5


def test_bulk_import(client: TestClient):
    response = client.post("/api/leads/bulk-import", json={
        "source": "digital_campaign",
        "leads": [
            {"name": "Lead One", "mobile": "9100000001", "source": "digital_campaign"},
            {"name": "Lead Two", "mobile": "9100000002", "source": "digital_campaign"},
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


def test_analytics_summary(client: TestClient):
    response = client.get("/api/leads/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_leads" in data
    assert "conversion_rate_percent" in data


def test_lead_not_found(client: TestClient):
    response = client.get("/api/leads/LEAD_NONEXISTENT")
    assert response.status_code == 404
