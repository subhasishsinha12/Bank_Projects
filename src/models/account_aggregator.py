"""
Account Aggregator Models — ReBIT / Sahamati Specification
Implements the Financial Information User (FIU) side of the AA framework.
Ref: https://api.rebit.org.in/
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Float, Integer, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from src.database import Base


class FIType(str, enum.Enum):
    """Financial Information types per ReBIT AA spec."""
    DEPOSIT             = "DEPOSIT"              # Bank accounts / FDs
    TERM_DEPOSIT        = "TERM_DEPOSIT"
    RECURRING_DEPOSIT   = "RECURRING_DEPOSIT"
    SIP                 = "SIP"
    CP                  = "CP"
    GOVT_SECURITIES     = "GOVT_SECURITIES"
    EQUITIES            = "EQUITIES"
    BONDS               = "BONDS"
    DEBENTURES          = "DEBENTURES"
    MUTUAL_FUNDS        = "MUTUAL_FUNDS"
    ETF                 = "ETF"
    IDR                 = "IDR"
    CIS                 = "CIS"
    AIF                 = "AIF"
    INSURANCE_POLICIES  = "INSURANCE_POLICIES"
    NPS                 = "NPS"
    INVIT               = "INVIT"
    REIT                = "REIT"
    GENERAL_INSURANCE   = "GENERAL_INSURANCE"
    GST_GSTR            = "GST_GSTR"
    TAX                 = "TAX"
    PENSION             = "PENSION"
    OTHER               = "OTHER"


class ConsentMode(str, enum.Enum):
    VIEW  = "VIEW"    # customer can view what data is shared
    STORE = "STORE"   # FIU can store data
    QUERY = "QUERY"   # FIU can query data
    STREAM = "STREAM" # data is streamed in real-time


class FetchType(str, enum.Enum):
    ONE_TIME  = "ONE_TIME"
    PERIODIC  = "PERIODIC"


class AAConsentStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACTIVE   = "ACTIVE"
    PAUSED   = "PAUSED"
    REVOKED  = "REVOKED"
    EXPIRED  = "EXPIRED"
    REJECTED = "REJECTED"


class AADataFetchStatus(str, enum.Enum):
    PENDING   = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"
    PARTIAL   = "PARTIAL"


class AAConsentArtefact(Base):
    """
    Tracks the full lifecycle of an AA consent request per ReBIT spec.
    One record per customer intent to share financial data.
    """
    __tablename__ = "aa_consent_artefacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # ReBIT identifiers
    txn_id       = Column(String(100), unique=True, index=True)   # UUID per API call
    consent_handle = Column(String(200), unique=True, index=True) # returned by AA on consent create
    consent_id   = Column(String(200), unique=True, index=True, nullable=True)  # set after approval

    customer_id  = Column(String, ForeignKey("customers.id"), nullable=False, index=True)

    # FIP / AA details
    aa_id        = Column(String(100))    # which AA (finvu, onemoney, phonepe)
    fip_ids      = Column(Text)           # JSON list of FIPs (source banks)
    fi_types     = Column(Text)           # JSON list of FIType values requested

    # Consent parameters (per ReBIT ConsentDetail object)
    purpose_code = Column(String(20))     # 101=wealth mgmt, 102=customer-spending, etc.
    purpose_text = Column(Text)
    consent_mode = Column(Text)           # JSON list of ConsentMode values
    fetch_type   = Column(SAEnum(FetchType), default=FetchType.ONE_TIME)

    # Data date range requested
    data_from    = Column(DateTime)
    data_to      = Column(DateTime)

    # Consent validity
    consent_start = Column(DateTime)
    consent_expiry = Column(DateTime)

    # Frequency (for PERIODIC)
    frequency_unit  = Column(String(20))   # MONTH, WEEK, DAY, HOUR, MIN, INF
    frequency_value = Column(Integer, default=1)

    # Status
    status       = Column(SAEnum(AAConsentStatus), default=AAConsentStatus.PENDING)
    redirect_url = Column(Text)           # URL to send customer to AA app

    # Callback / webhook received
    callback_received_at = Column(DateTime)
    rejection_reason     = Column(Text)

    # DPDP link
    dpdp_consent_id = Column(String, ForeignKey("consent_records.id"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer     = relationship("Customer", back_populates="aa_consents")
    data_fetches = relationship("AADataFetch", back_populates="consent")


class AADataFetch(Base):
    """
    Tracks each data fetch session against an approved AA consent.
    One consent can have multiple fetches (periodic).
    """
    __tablename__ = "aa_data_fetches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    consent_id  = Column(String, ForeignKey("aa_consent_artefacts.id"), nullable=False)
    customer_id = Column(String, nullable=False, index=True)

    # ReBIT session identifiers
    session_id  = Column(String(200), unique=True, index=True)
    txn_id      = Column(String(100))

    # Fetch metadata
    fi_types_fetched = Column(Text)       # JSON list actually fetched
    fip_id           = Column(String(100))
    status           = Column(SAEnum(AADataFetchStatus), default=AADataFetchStatus.PENDING)

    # Raw encrypted payload (JWE) — never store decrypted PII here
    encrypted_payload = Column(Text)

    # Parsed financial summary (non-PII aggregates only)
    accounts_found    = Column(Integer, default=0)
    data_date_range   = Column(String(100))
    fetch_error       = Column(Text)

    requested_at  = Column(DateTime, server_default=func.now())
    completed_at  = Column(DateTime)

    consent       = relationship("AAConsentArtefact", back_populates="data_fetches")
    linked_accounts = relationship("AALinkedAccount", back_populates="data_fetch")


class AALinkedAccount(Base):
    """
    A financial account discovered via AA (could be at another bank/FIP).
    Stores non-sensitive identifiers only; actual statement data goes to FinancialSummary.
    """
    __tablename__ = "aa_linked_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    data_fetch_id = Column(String, ForeignKey("aa_data_fetches.id"), nullable=False)
    customer_id   = Column(String, nullable=False, index=True)

    fip_id        = Column(String(100))          # FIP institution ID
    fip_name      = Column(String(200))          # human-readable FIP name
    masked_account_number = Column(String(50))   # e.g. XXXX1234
    account_type  = Column(String(50))           # SAVINGS, CURRENT, TERM_DEPOSIT
    fi_type       = Column(SAEnum(FIType))

    # Aggregated metrics (no raw transaction data stored)
    currency         = Column(String(10), default="INR")
    current_balance  = Column(Float)
    avg_monthly_balance = Column(Float)
    account_opened   = Column(String(20))        # YYYY-MM

    data_fetch = relationship("AADataFetch", back_populates="linked_accounts")


class FinancialSummary(Base):
    """
    AI-computed financial profile derived from AA bank statement data.
    Aggregates only — no raw transactions stored (DPDP data minimisation).
    Used for: credit pre-assessment, income verification, loan pre-approval.
    """
    __tablename__ = "financial_summaries"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, unique=True, index=True)

    # Computed from AA data
    verified_monthly_income   = Column(Float)      # median salary credit
    income_confidence         = Column(Float)      # 0-1 confidence score
    employer_verified         = Column(Boolean, default=False)
    employer_name_aa          = Column(String(200))

    avg_monthly_balance       = Column(Float)
    min_monthly_balance_6m    = Column(Float)
    max_monthly_balance_6m    = Column(Float)

    total_monthly_obligations = Column(Float)      # detected EMI outflows
    obligation_count          = Column(Integer, default=0)
    debt_to_income_ratio      = Column(Float)

    total_accounts_found      = Column(Integer, default=0)
    total_fips_linked         = Column(Integer, default=0)

    # Pre-approval outputs
    pre_approved_personal_loan = Column(Float)
    pre_approved_credit_card   = Column(Float)
    pre_approved_home_loan     = Column(Float)

    credit_behaviour_score     = Column(Float)     # 0-100 internal score
    bounced_cheques_6m         = Column(Integer, default=0)
    returned_emi_count_6m      = Column(Integer, default=0)

    # Statement period analyzed
    analysis_from   = Column(String(20))    # YYYY-MM-DD
    analysis_to     = Column(String(20))
    computed_at     = Column(DateTime, server_default=func.now())
    aa_consent_id   = Column(String, ForeignKey("aa_consent_artefacts.id"))

    customer = relationship("Customer", back_populates="financial_summary")
