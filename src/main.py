from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.database import create_tables
from src.api import customers, leads, onboarding, kyc, rekyc, ckyc
from src.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Bank Customer Acquisition & KYC Platform

A comprehensive AI-powered platform for:

- **Lead Management** — Capture, score, and qualify leads with ML-based scoring
- **Hyper-Personalisation** — Claude AI-driven product recommendations and messaging
- **Conversational Onboarding** — Natural language chat-based account opening (Arya bot)
- **KYC Management** — Document upload, OCR extraction, Aadhaar/PAN verification
- **Re-KYC** — Periodic KYC renewal tracking, reminders, and workflow
- **CKYC Registry** — Central KYC Registry search, registration, and updates

### Compliance
Designed per RBI KYC Master Directions, PMLA guidelines, and CERSAI CKYC norms.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    create_tables()


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "modules": [
            "Customer Management",
            "Lead Management & Scoring",
            "Conversational Onboarding (Arya)",
            "KYC Document Processing",
            "Re-KYC Workflow",
            "CKYC Registry Integration",
        ],
    }


app.include_router(customers.router)
app.include_router(leads.router)
app.include_router(onboarding.router)
app.include_router(kyc.router)
app.include_router(rekyc.router)
app.include_router(ckyc.router)
