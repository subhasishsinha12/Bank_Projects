from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import create_tables
from src.api import customers, leads, onboarding, kyc, rekyc, ckyc
from src.api import consent, account_aggregator
from src.middleware.consent_guard import ConsentAuditMiddleware
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="""
## Bank Customer Acquisition & KYC Platform

AI-powered platform with full regulatory compliance:

### Core Modules
- **Lead Management** — ML scoring, hot/warm/cold segmentation, bulk import
- **Hyper-Personalisation** — Claude AI product recommendations, persona tagging
- **Conversational Onboarding (Arya)** — natural-language KYC guidance
- **KYC Management** — document upload, OCR, Aadhaar OTP, PAN/NSDL
- **Re-KYC** — periodic renewal per RBI KYC Master Directions
- **CKYC Registry** — CERSAI integration for KYC KIN management

### New: Regulatory Compliance Layer
- **Account Aggregator (AA)** — ReBIT/Sahamati FIU integration for frictionless
  onboarding; bank-statement income verification; pre-approved credit limits
- **DPDP Consent Management** — Digital Personal Data Protection Act 2023;
  consent artefacts, withdrawal, Data Subject Requests, breach notification

### Compliance
RBI KYC Master Directions · PMLA 2002 · DPDP Act 2023 · ReBIT AA Spec v2.0 · CERSAI CKYC
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DPDP audit middleware — records every data-touching API call transparently
app.add_middleware(ConsentAuditMiddleware)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "2.0.0",
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.app_name,
        "version": "2.0.0",
        "docs": "/docs",
        "modules": [
            "Customer Management",
            "Lead Management & Scoring",
            "Conversational Onboarding (Arya)",
            "KYC Document Processing",
            "Re-KYC Workflow",
            "CKYC Registry Integration",
            "Account Aggregator (AA) — NEW",
            "DPDP Consent Management — NEW",
        ],
    }


# Core modules
app.include_router(customers.router)
app.include_router(leads.router)
app.include_router(onboarding.router)
app.include_router(kyc.router)
app.include_router(rekyc.router)
app.include_router(ckyc.router)

# New compliance modules
app.include_router(consent.router)
app.include_router(account_aggregator.router)
