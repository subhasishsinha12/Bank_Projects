"""
Account Aggregator Integration API
Implements the FIU (Financial Information User) side of the RBI AA framework.

Complete flow:
  1. POST /initiate        → customer approves → redirect to AA app
  2. POST /callback        → AA webhook after approval
  3. POST /fetch           → request + retrieve financial data
  4. GET  /summary/{id}    → computed financial profile
  5. GET  /pre-approval/{id} → pre-approved product limits
"""
import json
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.customer import Customer
from src.models.account_aggregator import (
    AAConsentArtefact, AADataFetch, AALinkedAccount, FinancialSummary,
    AAConsentStatus, AADataFetchStatus, FIType,
)
from src.models.consent import ConsentPurpose, DataCategory, LegalBasis
from src.schemas.account_aggregator import (
    AAConsentInitiate, AAConsentCallback, AADataFetchRequest,
    AAConsentResponse, AADataFetchResponse, LinkedAccountResponse,
    FinancialSummaryResponse, PreApprovalResponse,
)
from src.services.aa_client import aa_client
from src.services.financial_analyzer import financial_analyzer
from src.services.consent_manager import consent_manager
from src.config import settings

router = APIRouter(prefix="/api/account-aggregator", tags=["Account Aggregator (AA)"])


# ------------------------------------------------------------------ #
# Step 1 — Initiate AA Consent
# ------------------------------------------------------------------ #

@router.post("/initiate", response_model=dict, status_code=201)
def initiate_aa_consent(
    data: AAConsentInitiate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Start the AA consent flow for a customer.
    Creates a DPDP consent record, then calls the AA to generate a consent handle.
    Returns the redirect_url to send the customer to their AA app.
    """
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not customer.mobile:
        raise HTTPException(status_code=400,
                            detail="Customer mobile required for AA flow")

    # 1. Create DPDP consent artefact first (consent before data access)
    ip = request.client.host if request.client else None
    dpdp_record = consent_manager.create_consent(
        db=db,
        customer_id=data.customer_id,
        purpose=ConsentPurpose.ACCOUNT_AGGREGATOR,
        data_categories=[DataCategory.FINANCIAL_DATA, DataCategory.CREDIT_HISTORY,
                         DataCategory.PERSONAL_IDENTITY],
        legal_basis=LegalBasis.CONSENT,
        channel="web",
        ip_address=ip,
        expiry_days=365,
    )
    consent_manager.activate_consent(db, dpdp_record.id, actor="customer", ip=ip)

    # 2. Also create credit-assessment consent if not present
    if not consent_manager.has_active_consent(
            db, data.customer_id, ConsentPurpose.CREDIT_ASSESSMENT):
        ca_record = consent_manager.create_consent(
            db=db,
            customer_id=data.customer_id,
            purpose=ConsentPurpose.CREDIT_ASSESSMENT,
            data_categories=[DataCategory.FINANCIAL_DATA, DataCategory.CREDIT_HISTORY],
            legal_basis=LegalBasis.CONTRACT,
            channel="web",
            ip_address=ip,
        )
        consent_manager.activate_consent(db, ca_record.id, actor="customer", ip=ip)

    # 3. Call AA to create consent request
    aa_resp = aa_client.create_consent_request(
        customer_mobile=customer.mobile,
        customer_aa_handle=data.customer_aa_handle,
        fi_types=data.fi_types,
        purpose=data.purpose,
        fetch_type=data.fetch_type,
        data_date_range_months=data.data_date_range_months,
        aa_provider=data.aa_provider,
    )
    if not aa_resp.get("success"):
        raise HTTPException(status_code=502,
                            detail=f"AA error: {aa_resp.get('error', 'Unknown')}")

    # 4. Persist the consent artefact
    now = datetime.utcnow()
    artefact = AAConsentArtefact(
        txn_id=aa_resp["txn_id"],
        consent_handle=aa_resp["consent_handle"],
        customer_id=data.customer_id,
        aa_id=data.aa_provider,
        fi_types=json.dumps([ft.value for ft in data.fi_types]),
        purpose_text=data.purpose,
        fetch_type=data.fetch_type,
        data_from=now - timedelta(days=data.data_date_range_months * 30),
        data_to=now,
        consent_start=now,
        consent_expiry=now + timedelta(days=365),
        status=AAConsentStatus.PENDING,
        redirect_url=aa_resp["redirect_url"],
        dpdp_consent_id=dpdp_record.id,
    )
    db.add(artefact)
    db.commit()
    db.refresh(artefact)

    return {
        "artefact_id": artefact.id,
        "consent_handle": artefact.consent_handle,
        "redirect_url": artefact.redirect_url,
        "status": artefact.status.value,
        "dpdp_consent_id": dpdp_record.consent_id,
        "instruction": "Redirect the customer to redirect_url to approve consent in their AA app.",
        "sandbox": aa_resp.get("sandbox", False),
    }


# ------------------------------------------------------------------ #
# Step 2 — AA Callback (Webhook from AA after customer approves)
# ------------------------------------------------------------------ #

@router.post("/callback", response_model=dict)
async def aa_consent_callback(
    data: AAConsentCallback,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Webhook endpoint called by the AA when the customer approves or rejects.
    Validates the callback, updates consent status, and triggers data fetch.
    """
    artefact = db.query(AAConsentArtefact).filter(
        AAConsentArtefact.consent_handle == data.consent_handle
    ).first()
    if not artefact:
        raise HTTPException(status_code=404, detail="Consent handle not found")

    artefact.status = data.status
    artefact.callback_received_at = datetime.utcnow()

    if data.status == AAConsentStatus.ACTIVE:
        artefact.consent_id = data.consent_id
        # Trigger background data fetch immediately
        background_tasks.add_task(
            _fetch_financial_data_task,
            artefact_id=artefact.id,
            consent_id=data.consent_id,
            signed_consent=data.signed_consent or "",
        )
    elif data.status == AAConsentStatus.REJECTED:
        artefact.rejection_reason = data.rejection_reason

    db.commit()
    return {"status": "received", "artefact_id": artefact.id,
            "consent_status": data.status.value}


# ------------------------------------------------------------------ #
# Step 3 — Manual fetch trigger (for polling / retry)
# ------------------------------------------------------------------ #

@router.post("/fetch", response_model=AADataFetchResponse)
def trigger_data_fetch(
    data: AADataFetchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger (or re-trigger) a financial data fetch for an approved AA consent."""
    artefact = db.query(AAConsentArtefact).filter(
        AAConsentArtefact.id == data.consent_artefact_id
    ).first()
    if not artefact:
        raise HTTPException(status_code=404, detail="Consent artefact not found")
    if artefact.status != AAConsentStatus.ACTIVE:
        raise HTTPException(status_code=400,
                            detail=f"Consent is not active (status: {artefact.status.value}). "
                                   f"Customer must approve in their AA app first.")

    fi_types = json.loads(artefact.fi_types or "[]")
    session_resp = aa_client.request_fi_data(
        consent_id=artefact.consent_id,
        signed_consent=f"mock-signed-{artefact.consent_id}",
        fi_types=[FIType(ft) for ft in fi_types],
        data_from=artefact.data_from or datetime.utcnow() - timedelta(days=180),
        data_to=artefact.data_to or datetime.utcnow(),
    )
    if not session_resp.get("success"):
        raise HTTPException(status_code=502,
                            detail=f"FI request failed: {session_resp.get('error')}")

    fetch = AADataFetch(
        consent_id=artefact.id,
        customer_id=artefact.customer_id,
        session_id=session_resp["session_id"],
        txn_id=session_resp.get("txn_id"),
        fi_types_fetched=artefact.fi_types,
        status=AADataFetchStatus.PENDING,
    )
    db.add(fetch)
    db.commit()
    db.refresh(fetch)

    background_tasks.add_task(
        _complete_fetch_task,
        fetch_id=fetch.id,
        session_id=session_resp["session_id"],
        consent_id=artefact.consent_id or "",
        artefact_id=artefact.id,
    )
    return fetch


# ------------------------------------------------------------------ #
# Step 4 — Poll consent status (for apps that can't receive webhooks)
# ------------------------------------------------------------------ #

@router.get("/consent/{artefact_id}/status", response_model=dict)
def poll_consent_status(artefact_id: str, db: Session = Depends(get_db)):
    artefact = db.query(AAConsentArtefact).filter(
        AAConsentArtefact.id == artefact_id
    ).first()
    if not artefact:
        raise HTTPException(status_code=404, detail="Consent artefact not found")

    if artefact.status == AAConsentStatus.PENDING:
        # Poll AA for latest status
        aa_status = aa_client.get_consent_status(artefact.consent_handle)
        if aa_status.get("status") == "ACTIVE" and not artefact.consent_id:
            artefact.consent_id = aa_status.get("consent_id")
            artefact.status = AAConsentStatus.ACTIVE
            artefact.callback_received_at = datetime.utcnow()
            db.commit()

    return {
        "artefact_id": artefact_id,
        "consent_handle": artefact.consent_handle,
        "status": artefact.status.value,
        "consent_id": artefact.consent_id,
        "redirect_url": artefact.redirect_url,
    }


# ------------------------------------------------------------------ #
# Financial Summary & Pre-approval
# ------------------------------------------------------------------ #

@router.get("/summary/{customer_id}", response_model=FinancialSummaryResponse)
def get_financial_summary(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve the computed financial profile derived from AA data."""
    summary = db.query(FinancialSummary).filter(
        FinancialSummary.customer_id == customer_id
    ).first()
    if not summary:
        raise HTTPException(
            status_code=404,
            detail="No financial summary found. Complete the AA data fetch first.",
        )
    return summary


@router.get("/pre-approval/{customer_id}", response_model=PreApprovalResponse)
def get_pre_approval(customer_id: str, db: Session = Depends(get_db)):
    """
    Returns pre-approved product limits derived from verified AA financial data.
    Used during onboarding to offer instant product eligibility without document upload.
    """
    summary = db.query(FinancialSummary).filter(
        FinancialSummary.customer_id == customer_id
    ).first()
    if not summary:
        raise HTTPException(status_code=404,
                            detail="Run AA data fetch first to compute pre-approval.")

    products = []
    if summary.pre_approved_personal_loan and summary.pre_approved_personal_loan > 0:
        products.append({
            "product": "Personal Loan",
            "pre_approved_amount": summary.pre_approved_personal_loan,
            "currency": "INR",
            "indicative_rate": "10.5% p.a.",
            "tenure_months": 60,
        })
    if summary.pre_approved_credit_card and summary.pre_approved_credit_card > 0:
        products.append({
            "product": "Credit Card",
            "pre_approved_limit": summary.pre_approved_credit_card,
            "currency": "INR",
            "card_type": "Rewards Platinum",
        })
    if summary.pre_approved_home_loan and summary.pre_approved_home_loan > 0:
        products.append({
            "product": "Home Loan",
            "pre_approved_amount": summary.pre_approved_home_loan,
            "currency": "INR",
            "indicative_rate": "8.5% p.a.",
            "tenure_months": 240,
        })

    return PreApprovalResponse(
        customer_id=customer_id,
        verified_income_monthly=summary.verified_monthly_income,
        income_confidence_pct=round((summary.income_confidence or 0) * 100, 1),
        employer=summary.employer_name_aa,
        pre_approved_products=products,
        debt_to_income_ratio=summary.debt_to_income_ratio,
        credit_behaviour_score=summary.credit_behaviour_score,
    )


@router.get("/linked-accounts/{customer_id}", response_model=List[LinkedAccountResponse])
def list_linked_accounts(customer_id: str, db: Session = Depends(get_db)):
    """List all financial accounts discovered across FIPs for this customer."""
    fetches = db.query(AADataFetch).filter(
        AADataFetch.customer_id == customer_id,
        AADataFetch.status == AADataFetchStatus.COMPLETED,
    ).all()
    accounts = []
    for f in fetches:
        accounts.extend(
            db.query(AALinkedAccount).filter(
                AALinkedAccount.data_fetch_id == f.id
            ).all()
        )
    return accounts


@router.get("/consents/{customer_id}", response_model=List[AAConsentResponse])
def list_aa_consents(customer_id: str, db: Session = Depends(get_db)):
    return db.query(AAConsentArtefact).filter(
        AAConsentArtefact.customer_id == customer_id
    ).order_by(AAConsentArtefact.created_at.desc()).all()


@router.post("/consent/{artefact_id}/revoke", response_model=dict)
def revoke_aa_consent(artefact_id: str, db: Session = Depends(get_db)):
    """Revoke an AA consent — stops future data pulls and revokes the DPDP consent."""
    artefact = db.query(AAConsentArtefact).filter(
        AAConsentArtefact.id == artefact_id
    ).first()
    if not artefact:
        raise HTTPException(status_code=404, detail="Consent artefact not found")

    artefact.status = AAConsentStatus.REVOKED
    if artefact.dpdp_consent_id:
        try:
            consent_manager.revoke_consent(
                db, artefact.dpdp_consent_id, reason="aa_consent_revoked", actor="customer"
            )
        except ValueError:
            pass
    db.commit()
    return {"message": "AA consent revoked", "artefact_id": artefact_id}


@router.get("/analytics/summary", response_model=dict)
def aa_analytics(db: Session = Depends(get_db)):
    total_artefacts = db.query(AAConsentArtefact).count()
    active = db.query(AAConsentArtefact).filter(
        AAConsentArtefact.status == AAConsentStatus.ACTIVE
    ).count()
    completed_fetches = db.query(AADataFetch).filter(
        AADataFetch.status == AADataFetchStatus.COMPLETED
    ).count()
    customers_with_summary = db.query(FinancialSummary).count()

    return {
        "total_aa_consents": total_artefacts,
        "active_consents": active,
        "completed_data_fetches": completed_fetches,
        "customers_with_financial_profile": customers_with_summary,
    }


# ------------------------------------------------------------------ #
# Background tasks
# ------------------------------------------------------------------ #

def _fetch_financial_data_task(artefact_id: str, consent_id: str, signed_consent: str):
    db: Session = None
    try:
        from src.database import SessionLocal
        db = SessionLocal()
        artefact = db.query(AAConsentArtefact).filter(
            AAConsentArtefact.id == artefact_id
        ).first()
        if not artefact:
            return

        fi_types = json.loads(artefact.fi_types or "[]")
        session_resp = aa_client.request_fi_data(
            consent_id=consent_id,
            signed_consent=signed_consent,
            fi_types=[FIType(ft) for ft in fi_types],
            data_from=artefact.data_from or datetime.utcnow() - timedelta(days=180),
            data_to=artefact.data_to or datetime.utcnow(),
        )
        if not session_resp.get("success"):
            return

        fetch = AADataFetch(
            consent_id=artefact_id,
            customer_id=artefact.customer_id,
            session_id=session_resp["session_id"],
            fi_types_fetched=artefact.fi_types,
            status=AADataFetchStatus.PENDING,
        )
        db.add(fetch)
        db.commit()
        db.refresh(fetch)

        _complete_fetch_task(fetch.id, session_resp["session_id"], consent_id, artefact_id)
    except Exception:
        pass
    finally:
        if db:
            db.close()


def _complete_fetch_task(fetch_id: str, session_id: str, consent_id: str, artefact_id: str):
    db = None
    try:
        from src.database import SessionLocal
        db = SessionLocal()
        fetch = db.query(AADataFetch).filter(AADataFetch.id == fetch_id).first()
        if not fetch:
            return

        raw_data = aa_client.fetch_fi_data(session_id, consent_id)

        if raw_data.get("status") == "COMPLETED" or raw_data.get("FI"):
            fi_list = aa_client.decrypt_fi_data(raw_data)
            analysis = financial_analyzer.analyze(fi_list)

            # Persist linked accounts (non-PII summaries only)
            for fip_data in fi_list:
                for acct in fip_data.get("data", []):
                    bal = float(acct.get("Summary", {}).get("currentBalance", 0) or 0)
                    linked = AALinkedAccount(
                        data_fetch_id=fetch.id,
                        customer_id=fetch.customer_id,
                        fip_id=fip_data.get("fipID"),
                        masked_account_number=acct.get("maskedAccNumber"),
                        account_type=acct.get("Summary", {}).get("type"),
                        current_balance=bal,
                    )
                    db.add(linked)

            fetch.accounts_found = analysis.get("total_accounts_found", 0)
            fetch.status = AADataFetchStatus.COMPLETED
            fetch.completed_at = datetime.utcnow()

            # Upsert FinancialSummary
            existing = db.query(FinancialSummary).filter(
                FinancialSummary.customer_id == fetch.customer_id
            ).first()
            summary_data = financial_analyzer.format_for_db(
                analysis, fetch.customer_id, artefact_id
            )
            if existing:
                for k, v in summary_data.items():
                    if k != "customer_id":
                        setattr(existing, k, v)
            else:
                db.add(FinancialSummary(**summary_data))

            # Update customer with AA-verified income
            customer = db.query(Customer).filter(
                Customer.id == fetch.customer_id
            ).first()
            if customer and analysis.get("verified_monthly_income"):
                customer.aa_verified_income = analysis["verified_monthly_income"] * 12
                customer.aa_verified_at = datetime.utcnow()
                pre_loan = analysis.get("pre_approved_personal_loan", 0) or 0
                pre_cc   = analysis.get("pre_approved_credit_card", 0) or 0
                customer.aa_pre_approved_limit = max(pre_loan, pre_cc)

            db.commit()
        else:
            fetch.status = AADataFetchStatus.FAILED
            fetch.fetch_error = raw_data.get("error", "Unknown error from AA")
            db.commit()
    except Exception as e:
        if db:
            try:
                fetch = db.query(AADataFetch).filter(AADataFetch.id == fetch_id).first()
                if fetch:
                    fetch.status = AADataFetchStatus.FAILED
                    fetch.fetch_error = str(e)
                    db.commit()
            except Exception:
                pass
    finally:
        if db:
            db.close()
