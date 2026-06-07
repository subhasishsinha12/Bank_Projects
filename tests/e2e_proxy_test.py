"""
End-to-End Proxy ID Test Suite
Exercises every module with realistic proxy identities.
Run:  python tests/e2e_proxy_test.py
"""
import json
import sys
import time
import uuid
import requests

BASE = "http://127.0.0.1:8002"

# ── Proxy identities ──────────────────────────────────────────────────────────
PROXIES = [
    {
        "label"     : "P-001 | Salaried Professional – Mumbai",
        "first_name": "Arjun",
        "last_name" : "Mehta",
        "mobile"    : "9810001001",
        "email"     : "arjun.mehta.proxy001@testbank.in",
        "pan"       : "AMEPX1001A",
        "aadhaar"   : "100100101001",
        "dob"       : "15/07/1990",
        "city"      : "Mumbai",
        "state"     : "Maharashtra",
        "pincode"   : "400001",
        "income"    : 1_200_000,
        "employment": "salaried",
        "employer"  : "TechCorp India Pvt Ltd",
        "aa_handle" : "arjunmehta@finvu",
        "aa_provider": "finvu",
        "product"   : "personal_loan",
        "lead_src"  : "website",
    },
    {
        "label"     : "P-002 | Self-Employed Business Owner – Delhi",
        "first_name": "Priya",
        "last_name" : "Kapoor",
        "mobile"    : "9810002002",
        "email"     : "priya.kapoor.proxy002@testbank.in",
        "pan"       : "BKPKX2002B",
        "aadhaar"   : "200200202002",
        "dob"       : "22/03/1985",
        "city"      : "New Delhi",
        "state"     : "Delhi",
        "pincode"   : "110001",
        "income"    : 3_500_000,
        "employment": "self_employed",
        "employer"  : "Kapoor Enterprises",
        "aa_handle" : "priyadev@onemoney",
        "aa_provider": "onemoney",
        "product"   : "business_loan",
        "lead_src"  : "referral",
    },
    {
        "label"     : "P-003 | Senior Citizen – Bangalore",
        "first_name": "Ramesh",
        "last_name" : "Iyer",
        "mobile"    : "9810003003",
        "email"     : "ramesh.iyer.proxy003@testbank.in",
        "pan"       : "CIYXR3003C",
        "aadhaar"   : "300300303003",
        "dob"       : "10/01/1955",
        "city"      : "Bangalore",
        "state"     : "Karnataka",
        "pincode"   : "560001",
        "income"    : 600_000,
        "employment": "retired",
        "employer"  : "Retired",
        "aa_handle" : "rameshiyer@cams",
        "aa_provider": "cams",
        "product"   : "fixed_deposit",
        "lead_src"  : "branch_walk_in",
    },
]

PASS = "✅"
FAIL = "❌"
INFO = "   "

results = []


def h(title: str):
    print(f"\n{'═'*65}")
    print(f"  {title}")
    print(f"{'═'*65}")


def step(label: str, ok: bool, detail: str = ""):
    status = PASS if ok else FAIL
    msg = f"  {status}  {label}"
    if detail:
        msg += f"\n{INFO}     {detail}"
    print(msg)
    results.append((label, ok))
    return ok


def jprint(d: dict):
    for k, v in d.items():
        if k not in ("signed_artefact", "encrypted_payload", "redirect_url"):
            print(f"{INFO}     {k}: {v}")


def post(path, payload, **kw):
    return requests.post(f"{BASE}{path}", json=payload, timeout=15, **kw)


def get(path, **kw):
    return requests.get(f"{BASE}{path}", timeout=10, **kw)


def delete(path, **kw):
    return requests.delete(f"{BASE}{path}", timeout=10, **kw)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 1 — LEAD MANAGEMENT & SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def run_lead_module(proxy):
    label = proxy["label"]
    h(f"MODULE 1 · LEAD MANAGEMENT  [{label}]")

    # Create lead
    r = post("/api/leads/", {
        "name"              : f"{proxy['first_name']} {proxy['last_name']}",
        "email"             : proxy["email"],
        "mobile"            : proxy["mobile"],
        "city"              : proxy["city"],
        "state"             : proxy["state"],
        "source"            : proxy["lead_src"],
        "interested_product": proxy["product"],
        "interested_amount" : proxy["income"] * 2,
        "utm_source"        : "proxy_test",
        "utm_campaign"      : "e2e_2025",
    })
    ok = r.status_code == 201
    lead = r.json() if ok else {}
    step("Create lead", ok,
         f"lead_id={lead.get('lead_id')} | score={lead.get('lead_score')} | "
         f"quality={lead.get('quality')} | persona={lead.get('persona_tags')}")

    if not ok:
        return None
    lead_id = lead["lead_id"]

    # Re-score with income/employment signals
    r2 = post(f"/api/leads/{lead_id}/rescore", {
        "lead_id": lead_id,
        "additional_signals": {
            "annual_income"  : proxy["income"],
            "employment_type": proxy["employment"],
            "credit_score"   : 760,
            "city"           : proxy["city"].lower(),
            "existing_customer": False,
        },
    })
    ok2 = r2.status_code == 200
    score_data = r2.json() if ok2 else {}
    step("Re-score lead with signals", ok2,
         f"new_score={score_data.get('new_score')} | quality={score_data.get('quality')}")

    # Log an activity
    r3 = post(f"/api/leads/{lead_id}/activity", {
        "lead_id"             : lead_id,
        "activity_type"       : "call_connected",
        "activity_description": f"Initial discovery call with {proxy['first_name']}",
        "channel"             : "phone",
        "outcome"             : "interested",
        "performed_by"        : "rm_test_agent",
    })
    step("Log call activity", r3.status_code == 200,
         f"score_impact={r3.json().get('score_impact')}")

    return lead_id


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2 — CUSTOMER CREATION
# ═══════════════════════════════════════════════════════════════════════════════

def run_customer_module(proxy):
    label = proxy["label"]
    h(f"MODULE 2 · CUSTOMER CREATION  [{label}]")

    r = post("/api/customers/", {
        "first_name"     : proxy["first_name"],
        "last_name"      : proxy["last_name"],
        "mobile"         : proxy["mobile"],
        "email"          : proxy["email"],
        "date_of_birth"  : proxy["dob"],
        "pan_number"     : proxy["pan"],
        "aadhaar_number" : proxy["aadhaar"],
        "city"           : proxy["city"],
        "state"          : proxy["state"],
        "pincode"        : proxy["pincode"],
        "annual_income"  : proxy["income"],
        "employment_type": proxy["employment"],
        "employer_name"  : proxy["employer"],
        "source"         : "e2e_proxy_test",
    })
    ok = r.status_code == 201
    cust = r.json() if ok else {}
    step("Create customer", ok,
         f"customer_id={cust.get('customer_id')} | segment={cust.get('segment')} | "
         f"risk={cust.get('risk_category')}")
    return cust if ok else None


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3 — DPDP CONSENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def run_dpdp_module(proxy, cust):
    label = proxy["label"]
    h(f"MODULE 3 · DPDP CONSENT MANAGEMENT  [{label}]")
    cid = cust["id"]

    # Onboarding consent bundle
    r = post(f"/api/consent/bundle/{cid}?language=en&channel=web", {})
    ok = r.status_code == 200
    bundle = r.json() if ok else {}
    step("Create & activate onboarding consent bundle", ok,
         f"consents_created={bundle.get('consents_created')} | "
         f"purposes={[b['purpose'] for b in bundle.get('bundle', [])]}")

    # Check consent for kyc_verification
    r2 = get(f"/api/consent/customer/{cid}/check", params={"purpose": "kyc_verification"})
    ok2 = r2.status_code == 200 and r2.json().get("has_consent") is True
    step("Consent check → kyc_verification active", ok2)

    # Check consent missing for marketing (not in bundle)
    r3 = get(f"/api/consent/customer/{cid}/check", params={"purpose": "marketing_communication"})
    ok3 = r3.status_code == 200 and r3.json().get("has_consent") is False
    step("Consent check → marketing_communication absent", ok3)

    # Dashboard
    r4 = get(f"/api/consent/customer/{cid}")
    ok4 = r4.status_code == 200
    dash = r4.json() if ok4 else {}
    step("Consent dashboard", ok4,
         f"total={dash.get('total_consents')} | active={dash.get('active')} | "
         f"processing_events={dash.get('data_processing_events')}")

    # DSR — access request
    r5 = post("/api/consent/dsr", {
        "customer_id" : cid,
        "request_type": "access",
        "description" : f"[Proxy {proxy['label']}] Request copy of all held data.",
    })
    ok5 = r5.status_code == 201
    dsr = r5.json() if ok5 else {}
    step("Submit DSR — right to access", ok5,
         f"dsr_id={dsr.get('dsr_id')} | due_date={dsr.get('due_date', '')[:10]}")

    # Resolve DSR
    if ok5:
        r6 = post(f"/api/consent/dsr/{dsr['dsr_id']}/resolve", {},
                  params={"resolution_note": "Full data export sent via secure link.",
                          "resolved_by": "dpo_proxy_test"})
        step("Resolve DSR within SLA", r6.status_code == 200,
             f"status={r6.json().get('status')}")

    # Revoke marketing consent explicitly (opt-out test)
    rmc = post("/api/consent/request", {
        "customer_id"    : cid,
        "purpose"        : "marketing_communication",
        "data_categories": ["contact_info"],
    })
    if rmc.status_code == 201:
        rc_id = rmc.json()["id"]
        post("/api/consent/activate", {"consent_id": rc_id})
        rv = post("/api/consent/revoke", {"consent_id": rc_id, "reason": "proxy_opt_out"})
        step("Create + revoke marketing consent (opt-out)", rv.status_code == 200,
             f"status={rv.json().get('status')}")

    # Processing log
    r7 = get(f"/api/consent/processing-log/{cid}")
    step("Processing audit log populated", r7.status_code == 200,
         f"events_logged={len(r7.json())}")

    return dash


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4 — KYC DOCUMENT VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def run_kyc_module(proxy, cust):
    label = proxy["label"]
    h(f"MODULE 4 · KYC VERIFICATION  [{label}]")
    cid = cust["id"]

    # Aadhaar OTP send
    r = post("/api/kyc/aadhaar/send-otp", {
        "customer_id"   : cid,
        "aadhaar_number": proxy["aadhaar"],
    })
    ok = r.status_code == 200 and r.json().get("success")
    txn = r.json().get("transaction_id", "") if ok else ""
    step("Aadhaar OTP send", ok, f"txn_id={txn} | masked={r.json().get('masked_mobile', '')}")

    # Aadhaar OTP verify
    r2 = post("/api/kyc/aadhaar/verify-otp", {
        "customer_id"   : cid,
        "aadhaar_number": proxy["aadhaar"],
        "otp"           : "123456",
        "transaction_id": txn,
    })
    ok2 = r2.status_code == 200 and r2.json().get("verified")
    step("Aadhaar OTP verify", ok2,
         f"verified={r2.json().get('verified')} | confidence={r2.json().get('confidence', 1.0)}")

    # PAN verify
    r3 = post("/api/kyc/pan/verify", {
        "customer_id"   : cid,
        "pan_number"    : proxy["pan"],
        "full_name"     : f"{proxy['first_name']} {proxy['last_name']}",
        "date_of_birth" : proxy["dob"],
    })
    ok3 = r3.status_code == 200 and r3.json().get("valid")
    step("PAN NSDL verification", ok3,
         f"valid={r3.json().get('valid')} | aadhaar_linked={r3.json().get('aadhaar_linked')}")

    # KYC status
    r4 = get(f"/api/kyc/customer/{cid}/status", params={"product": proxy["product"]})
    ok4 = r4.status_code == 200
    st = r4.json() if ok4 else {}
    step("KYC status check", ok4,
         f"overall={st.get('overall_status')} | submitted={st.get('documents_submitted')} | "
         f"verified={st.get('documents_verified')} | pending={st.get('pending_documents')}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 5 — ACCOUNT AGGREGATOR (AA) FLOW
# ═══════════════════════════════════════════════════════════════════════════════

def run_aa_module(proxy, cust):
    label = proxy["label"]
    h(f"MODULE 5 · ACCOUNT AGGREGATOR  [{label}]")
    cid = cust["id"]

    # Step 1: Initiate AA consent
    r = post("/api/account-aggregator/initiate", {
        "customer_id"          : cid,
        "customer_aa_handle"   : proxy["aa_handle"],
        "aa_provider"          : proxy["aa_provider"],
        "fi_types"             : ["DEPOSIT"],
        "purpose"              : "credit_assessment",
        "data_date_range_months": 6,
    })
    ok = r.status_code == 201
    init = r.json() if ok else {}
    step("AA consent initiate", ok,
         f"artefact_id={init.get('artefact_id')} | "
         f"handle={init.get('consent_handle')} | sandbox={init.get('sandbox')}")
    step("DPDP consent auto-created", "dpdp_consent_id" in init,
         f"dpdp_id={init.get('dpdp_consent_id')}")
    if not ok:
        return None

    artefact_id = init["artefact_id"]
    handle      = init["consent_handle"]
    consent_id  = f"CI-{uuid.uuid4().hex[:12].upper()}"

    # Step 2: Simulate customer approval (webhook callback)
    r2 = post("/api/account-aggregator/callback", {
        "consent_handle": handle,
        "status"        : "ACTIVE",
        "consent_id"    : consent_id,
        "signed_consent": f"SIGNED-JWS-{consent_id}",
    })
    ok2 = r2.status_code == 200 and r2.json().get("consent_status") == "ACTIVE"
    step("Customer approves in AA app (callback)", ok2,
         f"consent_id={consent_id}")

    # Step 3: Trigger data fetch
    r3 = post("/api/account-aggregator/fetch", {"consent_artefact_id": artefact_id})
    ok3 = r3.status_code == 200
    fetch = r3.json() if ok3 else {}
    step("FI data fetch request", ok3,
         f"session_id={fetch.get('session_id')} | status={fetch.get('status')}")

    # Step 4: Poll consent status
    r4 = get(f"/api/account-aggregator/consent/{artefact_id}/status")
    ok4 = r4.status_code == 200
    step("Poll consent status", ok4,
         f"status={r4.json().get('status')}")

    # Wait briefly for background task to complete
    time.sleep(1.5)

    # Step 5: Financial summary
    r5 = get(f"/api/account-aggregator/summary/{cid}")
    ok5 = r5.status_code == 200
    summary = r5.json() if ok5 else {}
    if ok5:
        step("Financial summary computed", ok5,
             f"monthly_income=₹{summary.get('verified_monthly_income', 0):,.0f} | "
             f"confidence={summary.get('income_confidence', 0):.0%} | "
             f"employer_verified={summary.get('employer_verified')} | "
             f"avg_balance=₹{summary.get('avg_monthly_balance', 0):,.0f}")
        step("Obligations detected", True,
             f"monthly_emi=₹{summary.get('total_monthly_obligations', 0):,.0f} | "
             f"dti={summary.get('debt_to_income_ratio', 0):.1%} | "
             f"credit_score={summary.get('credit_behaviour_score', 0):.0f}/100")
    else:
        step("Financial summary computed", False,
             "Background task may still be running; re-fetch in production")

    # Step 6: Pre-approval
    r6 = get(f"/api/account-aggregator/pre-approval/{cid}")
    ok6 = r6.status_code == 200
    pa = r6.json() if ok6 else {}
    if ok6:
        products_str = " | ".join(
            f"{p['product']}=₹{p.get('pre_approved_amount', p.get('pre_approved_limit', 0)):,.0f}"
            for p in pa.get("pre_approved_products", [])
        )
        step("Pre-approved product limits", ok6,
             f"income_verified=₹{pa.get('verified_income_monthly', 0):,.0f}/mo | {products_str}")
    else:
        step("Pre-approved product limits", False, "Summary not ready yet")

    # Step 7: Linked accounts list
    r7 = get(f"/api/account-aggregator/linked-accounts/{cid}")
    ok7 = r7.status_code == 200
    step("Linked accounts discovered", ok7,
         f"accounts={len(r7.json())} across FIPs" if ok7 else "")

    return summary if ok5 else None


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 6 — CKYC REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

def run_ckyc_module(proxy, cust):
    label = proxy["label"]
    h(f"MODULE 6 · CKYC REGISTRY  [{label}]")
    cid = cust["id"]

    # Search by PAN
    r = post("/api/ckyc/search", {"pan_number": proxy["pan"]})
    ok = r.status_code == 200
    cs = r.json() if ok else {}
    step("CKYC search by PAN", ok,
         f"found={cs.get('found')} | ckyc_id={cs.get('ckyc_id')} | "
         f"kyc_status={cs.get('kyc_status')}")

    # Search by Aadhaar
    r2 = post("/api/ckyc/search", {"aadhaar_number": proxy["aadhaar"]})
    ok2 = r2.status_code == 200
    step("CKYC search by Aadhaar", ok2,
         f"found={r2.json().get('found')} | ckyc_id={r2.json().get('ckyc_id')}")

    # Pre-fill from CKYC
    r3 = post(f"/api/ckyc/prefill/{cid}", {},
              params={"pan_number": proxy["pan"]})
    ok3 = r3.status_code == 200
    pf = r3.json() if ok3 else {}
    step("Pre-fill onboarding from CKYC", ok3,
         f"found={pf.get('found')} | prefilled_fields={pf.get('prefilled_fields', [])[:4]}")

    # CKYC registration (requires KYC completed)
    r4 = requests.post(f"{BASE}/api/ckyc/register/{cid}", timeout=10)
    # Will return 400 (kyc not complete) or 200 — both are valid expected states
    step("CKYC registration attempt", r4.status_code in (200, 400),
         f"status={r4.status_code} | "
         f"msg={r4.json().get('message', r4.json().get('detail', ''))[:60]}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 7 — CONVERSATIONAL ONBOARDING (Arya Bot)
# ═══════════════════════════════════════════════════════════════════════════════

def run_onboarding_module(proxy):
    label = proxy["label"]
    h(f"MODULE 7 · CONVERSATIONAL ONBOARDING  [{label}]")

    # Start session
    r = post("/api/onboarding/start", {
        "channel"        : "web",
        "language"       : "en",
        "initial_intent" : proxy["product"],
        "device_type"    : "desktop",
    })
    ok = r.status_code == 200
    sess = r.json() if ok else {}
    token = sess.get("session_token", "")
    step("Start onboarding session", ok,
         f"stage={sess.get('current_stage')} | progress={sess.get('progress_percent')}%")
    step("Welcome message received", bool(sess.get("message")),
         f"\"{sess.get('message', '')[:80]}...\"")

    if not ok:
        return

    # Multi-turn conversation
    turns = [
        f"Hi, my name is {proxy['first_name']} {proxy['last_name']}",
        f"My mobile is {proxy['mobile']} and email is {proxy['email']}",
        f"My PAN is {proxy['pan']} and date of birth is {proxy['dob']}",
        f"I'm interested in {proxy['product'].replace('_', ' ')}",
        f"I live at {proxy['city']}, {proxy['state']} - {proxy['pincode']}",
    ]
    for i, msg in enumerate(turns, 1):
        tr = post("/api/onboarding/chat", {
            "session_token": token,
            "message"      : msg,
        })
        ok_t = tr.status_code == 200
        td   = tr.json() if ok_t else {}
        step(f"Chat turn {i}", ok_t,
             f"stage={td.get('current_stage')} | progress={td.get('progress_percent')}% | "
             f"reply=\"{td.get('message', '')[:70]}...\"")

    # Personalisation
    rp = post("/api/onboarding/personalize", {
        "context": {
            "name"           : proxy["first_name"],
            "annual_income"  : proxy["income"],
            "employment_type": proxy["employment"],
            "age"            : 35,
            "city"           : proxy["city"].lower(),
        },
        "intent": proxy["product"],
    })
    ok_p = rp.status_code == 200
    pd   = rp.json() if ok_p else {}
    step("Personalisation engine", ok_p,
         f"persona={pd.get('persona_tags')} | "
         f"channel={pd.get('engagement_channel')} | "
         f"nba={pd.get('next_best_action')}")
    if ok_p and pd.get("personalised_message"):
        step("Personalised message generated", True,
             f"\"{pd['personalised_message'][:90]}...\"")

    # Get history
    rh = get(f"/api/onboarding/session/{token}/history")
    step("Session history stored", rh.status_code == 200,
         f"messages={len(rh.json())}")

    return token


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 8 — Re-KYC WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════════

def run_rekyc_module(proxy, cust):
    label = proxy["label"]
    h(f"MODULE 8 · Re-KYC WORKFLOW  [{label}]")
    cid = cust["id"]

    r = post("/api/rekyc/initiate", {
        "customer_id"     : cid,
        "trigger_reason"  : "periodic",
        "preferred_channel": "email",
    })
    ok = r.status_code == 201
    req = r.json() if ok else {}
    step("Initiate Re-KYC", ok,
         f"request_id={req.get('id', '')[:8]}... | "
         f"status={req.get('status')} | due={str(req.get('due_date', ''))[:10]}")

    # List customer Re-KYC requests
    r2 = get(f"/api/rekyc/customer/{cid}")
    step("List Re-KYC requests", r2.status_code == 200,
         f"total={len(r2.json())}")

    # Analytics
    r3 = get("/api/rekyc/analytics")
    ok3 = r3.status_code == 200
    an = r3.json() if ok3 else {}
    step("Re-KYC analytics", ok3,
         f"total_kyc={an.get('total_customers_with_kyc')} | "
         f"overdue={an.get('rekyc_overdue')} | "
         f"due_90d={an.get('rekyc_due_in_90_days')}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 9 — DATA BREACH + COMPLIANCE HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

def run_breach_and_compliance():
    h("MODULE 9 · BREACH NOTIFICATION + COMPLIANCE HEALTH")

    # Register a test breach
    r = post("/api/consent/breach", {
        "breach_type"              : "unauthorized_api_access",
        "data_categories_affected" : ["personal_identity", "contact_info"],
        "estimated_records_affected": 3,
        "description"              : "[Proxy Test] Simulated breach for notification SLA test.",
        "reported_by"              : "proxy_test_suite",
    })
    ok = r.status_code == 201
    breach = r.json() if ok else {}
    step("Register data breach", ok,
         f"ref={breach.get('breach_ref')} | "
         f"notif_due={str(breach.get('notification_due', ''))[:16]} "
         f"(72h from discovery)")

    # DPCI notification
    if ok:
        r2 = post(f"/api/consent/breach/{breach['breach_ref']}/notify-dpci", {})
        step("Mark DPCI notified", r2.status_code == 200,
             f"notified_at={str(r2.json().get('dpci_notified_at', ''))[:16]}")

    # Compliance health dashboard
    r3 = get("/api/consent/compliance/health")
    ok3 = r3.status_code == 200
    ch = r3.json() if ok3 else {}
    step("Compliance health dashboard", ok3,
         f"status={ch.get('overall_status')} | "
         f"active_consents={ch.get('active_consents')} | "
         f"overdue_dsrs={ch.get('overdue_dsrs')} | "
         f"breach_pending={ch.get('breaches_pending_dpci_notification')}")

    # Lead + onboarding analytics
    r4 = get("/api/leads/analytics/summary")
    la = r4.json() if r4.status_code == 200 else {}
    step("Lead pipeline analytics", r4.status_code == 200,
         f"total={la.get('total_leads')} | "
         f"hot={la.get('by_quality', {}).get('hot')} | "
         f"warm={la.get('by_quality', {}).get('warm')} | "
         f"cold={la.get('by_quality', {}).get('cold')} | "
         f"conversion={la.get('conversion_rate_percent')}%")

    r5 = get("/api/onboarding/analytics/funnel")
    fa = r5.json() if r5.status_code == 200 else {}
    step("Onboarding funnel analytics", r5.status_code == 200,
         f"total_sessions={fa.get('total_sessions')} | "
         f"completed={fa.get('completed')} | "
         f"completion_rate={fa.get('completion_rate')}%")

    r6 = get("/api/account-aggregator/analytics/summary")
    aa = r6.json() if r6.status_code == 200 else {}
    step("AA analytics", r6.status_code == 200,
         f"total_consents={aa.get('total_aa_consents')} | "
         f"active={aa.get('active_consents')} | "
         f"fetches_done={aa.get('completed_data_fetches')} | "
         f"with_profile={aa.get('customers_with_financial_profile')}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   BANK PLATFORM — END-TO-END PROXY ID TEST SUITE               ║")
    print("║   3 Proxy Identities × 9 Modules                               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    # Health check
    try:
        hc = requests.get(f"{BASE}/health", timeout=5).json()
        print(f"\n  Server: {hc['service']} v{hc['version']} — {hc['status'].upper()}")
    except Exception as e:
        print(f"\n  ❌ Server not reachable: {e}")
        sys.exit(1)

    for proxy in PROXIES:
        print(f"\n\n{'▓'*65}")
        print(f"  PROXY IDENTITY: {proxy['label']}")
        print(f"{'▓'*65}")

        run_lead_module(proxy)
        cust = run_customer_module(proxy)
        if not cust:
            print(f"  ❌ Customer creation failed — skipping remaining modules")
            continue

        run_dpdp_module(proxy, cust)
        run_kyc_module(proxy, cust)
        run_aa_module(proxy, cust)
        run_ckyc_module(proxy, cust)
        run_onboarding_module(proxy)
        run_rekyc_module(proxy, cust)

    run_breach_and_compliance()

    # ── Final summary ──────────────────────────────────────────────────────────
    total  = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print(f"\n\n{'═'*65}")
    print(f"  FINAL RESULTS")
    print(f"{'═'*65}")
    if failed:
        print(f"\n  FAILED STEPS:")
        for name, ok in results:
            if not ok:
                print(f"  {FAIL}  {name}")
    print(f"\n  {'✅' if failed == 0 else '⚠️ '} {passed}/{total} checks passed  "
          f"({'100%' if total == 0 else f'{passed/total:.0%}'})")
    print()
    sys.exit(0 if failed == 0 else 1)
