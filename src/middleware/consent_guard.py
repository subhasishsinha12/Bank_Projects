"""
DPDP Consent Guard — FastAPI Middleware & Dependency
Two enforcement mechanisms:

1. ConsentGuard dependency — injected per-route via Depends().
   Checks that the customer has active consent for the operation.
   Usage: add `_: None = Depends(require_consent(purpose))` to any endpoint.

2. ConsentAuditMiddleware — Starlette middleware that records every
   data-processing event transparently, without modifying route logic.
"""
import json
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.consent import ConsentPurpose, DataCategory, LegalBasis
from src.services.consent_manager import consent_manager, ENDPOINT_CONSENT_MAP


# Endpoints that never require consent (health checks, auth, consent management itself)
CONSENT_EXEMPT_PATHS = {
    "/health", "/", "/docs", "/redoc", "/openapi.json",
    "/api/consent",          # consent management endpoints themselves
    "/api/onboarding/start", # first touch — no customer_id yet
}

# Endpoints that require consent but have legal basis = regulatory mandate
LEGAL_OBLIGATION_PATHS = {
    "/api/ckyc",
    "/api/kyc/aadhaar",
    "/api/kyc/pan",
    "/api/rekyc",
}


def require_consent(
    purpose: ConsentPurpose,
    data_categories: Optional[list] = None,
    exempt_if_legal_obligation: bool = False,
):
    """
    FastAPI Depends()-compatible factory for per-endpoint consent enforcement.

    Usage:
        @router.get("/sensitive-data")
        def endpoint(
            customer_id: str,
            _: None = Depends(require_consent(ConsentPurpose.CREDIT_ASSESSMENT))
        ):
            ...
    """
    def _dependency(request: Request):
        if exempt_if_legal_obligation:
            return None

        customer_id = (
            request.query_params.get("customer_id")
            or request.path_params.get("customer_id")
        )
        if not customer_id:
            return None   # cannot enforce without customer_id; route handles auth

        db: Session = SessionLocal()
        try:
            error = consent_manager.enforce_for_endpoint(
                db, customer_id, request.url.path
            )
            if error:
                raise HTTPException(status_code=451, detail={
                    "error": "CONSENT_REQUIRED",
                    "message": error,
                    "purpose": purpose.value,
                    "obtain_consent_url": f"/api/consent/request/{customer_id}",
                })
        finally:
            db.close()

    return _dependency


class ConsentAuditMiddleware(BaseHTTPMiddleware):
    """
    Transparent middleware that records data-processing events for all
    API calls that touch PII, fulfilling DPDP §11 audit-trail requirements.
    Runs AFTER the response is generated so it never blocks requests.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._exempt = CONSENT_EXEMPT_PATHS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Only audit successful data-touching requests
        path = request.url.path
        if (response.status_code < 400
                and not any(path.startswith(e) for e in self._exempt)
                and any(path.startswith(p) for p in ENDPOINT_CONSENT_MAP)):
            try:
                self._record_processing(request, path)
            except Exception:
                pass   # audit failure must never break the response

        return response

    def _record_processing(self, request: Request, path: str):
        mapping = None
        for pattern, m in ENDPOINT_CONSENT_MAP.items():
            if path.startswith(pattern):
                mapping = m
                break
        if not mapping:
            return

        customer_id = (
            request.query_params.get("customer_id")
            or request.path_params.get("customer_id")
        )
        if not customer_id:
            return

        db: Session = SessionLocal()
        try:
            method_op = {
                "GET": "read", "POST": "write",
                "PATCH": "write", "PUT": "write", "DELETE": "delete",
            }.get(request.method, "read")

            consent_manager.record_processing(
                db=db,
                customer_id=customer_id,
                operation=method_op,
                data_categories=mapping.get("categories", []),
                api_endpoint=path,
                legal_basis="legal_obligation" if any(
                    path.startswith(p) for p in LEGAL_OBLIGATION_PATHS
                ) else "consent",
                processed_by="api",
            )
        finally:
            db.close()
