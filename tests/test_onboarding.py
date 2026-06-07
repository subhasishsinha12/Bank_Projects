"""Tests for Conversational Onboarding APIs"""
import pytest
from fastapi.testclient import TestClient


def test_start_session(client: TestClient):
    response = client.post("/api/onboarding/start", json={
        "channel": "web",
        "language": "en",
        "initial_intent": "savings_account",
    })
    assert response.status_code == 200
    data = response.json()
    assert "session_token" in data
    assert data["current_stage"] == "welcome"
    assert data["progress_percent"] == 5
    assert "message" in data


def test_chat_message(client: TestClient):
    start = client.post("/api/onboarding/start", json={"channel": "web"})
    token = start.json()["session_token"]

    response = client.post("/api/onboarding/chat", json={
        "session_token": token,
        "message": "Hi, my name is Sunita Patel",
    })
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "current_stage" in data
    assert data["session_token"] == token


def test_get_session(client: TestClient):
    start = client.post("/api/onboarding/start", json={"channel": "mobile_app"})
    token = start.json()["session_token"]

    response = client.get(f"/api/onboarding/session/{token}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_token"] == token
    assert data["is_active"] is True


def test_session_history(client: TestClient):
    start = client.post("/api/onboarding/start", json={"channel": "web"})
    token = start.json()["session_token"]

    client.post("/api/onboarding/chat", json={
        "session_token": token,
        "message": "I want to open a savings account",
    })

    response = client.get(f"/api/onboarding/session/{token}/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 2  # welcome + user message + assistant reply


def test_abandon_session(client: TestClient):
    start = client.post("/api/onboarding/start", json={"channel": "web"})
    token = start.json()["session_token"]

    response = client.post(f"/api/onboarding/session/{token}/abandon")
    assert response.status_code == 200


def test_personalize(client: TestClient):
    response = client.post("/api/onboarding/personalize", json={
        "context": {
            "name": "Ravi",
            "annual_income": 1500000,
            "employment_type": "salaried",
            "age": 28,
            "city": "bangalore",
        },
        "intent": "savings_account",
    })
    assert response.status_code == 200
    data = response.json()
    assert "persona_tags" in data
    assert "recommended_products" in data
    assert "personalised_message" in data
    assert "next_best_action" in data


def test_funnel_analytics(client: TestClient):
    response = client.get("/api/onboarding/analytics/funnel")
    assert response.status_code == 200
    data = response.json()
    assert "total_sessions" in data
    assert "completion_rate" in data


def test_invalid_session_token(client: TestClient):
    response = client.post("/api/onboarding/chat", json={
        "session_token": "invalid_token_xyz",
        "message": "Hello",
    })
    assert response.status_code == 404
