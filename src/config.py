from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Bank Customer Acquisition & KYC Platform"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./bank_kyc.db"

    # Anthropic AI
    anthropic_api_key: Optional[str] = None
    ai_model: str = "claude-sonnet-4-6"

    # Security
    secret_key: str = "change-this-in-production-use-strong-random-key"
    access_token_expire_minutes: int = 60

    # CKYC Registry
    ckyc_api_base_url: str = "https://www.ckycreg.com/api/v1"
    ckyc_api_key: Optional[str] = None
    ckyc_institution_id: Optional[str] = None

    # Storage
    azure_storage_connection_string: Optional[str] = None
    kyc_documents_container: str = "kyc-documents"

    # Lead Scoring thresholds
    lead_score_hot: int = 75
    lead_score_warm: int = 50
    lead_score_cold: int = 0

    # ReKYC
    rekyc_validity_years: int = 10
    rekyc_reminder_days: int = 90

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
