from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from .db import Base


class Borrower(Base):
    __tablename__ = "borrowers"

    id = Column(String, primary_key=True)
    name = Column(String)
    sector = Column(String)
    district = Column(String)
    loan_amount = Column(Float)
    gender = Column(String)
    dscr = Column(Float)
    current_ratio = Column(Float)
    tol_tnw = Column(Float)
    cmr_score = Column(Float)
    vintage_years = Column(Float)
    collateral_pct = Column(Float)
    gst_compliance = Column(Float)
    upi_txn_drop = Column(Float)
    sector_stress = Column(Float)
    bureau_dpd = Column(Float)
    default_flag = Column(Integer)
    pd_current = Column(Float)
    pd_history = Column(JSON)
    ews_stage = Column(String)
    inas_stage = Column(String)
    sicr_alert = Column(Boolean)
    top_risk_drivers = Column(JSON)


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(String, primary_key=True)
    name = Column(String)
    model_type = Column(String)
    purpose = Column(String)
    owner = Column(String)
    tier = Column(Integer)
    status = Column(String)
    validation_status = Column(String)
    last_validated = Column(String)
    psi_current = Column(Float)
    gini = Column(Float, nullable=True)
    auc = Column(Float, nullable=True)
    use_scope = Column(String)
    notes = Column(Text, default="")


class PSIHistory(Base):
    __tablename__ = "psi_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String)
    month = Column(String)
    psi_value = Column(Float)


class CompliancePrinciple(Base):
    __tablename__ = "compliance_principles"

    id = Column(String, primary_key=True)
    name = Column(String)
    status = Column(String)
    score = Column(Float)
    gap = Column(Text)


class EWSAlert(Base):
    __tablename__ = "ews_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    borrower_id = Column(String)
    borrower_name = Column(String)
    alert_type = Column(String)
    trigger_reason = Column(String)
    shap_driver = Column(String)
    raised_at = Column(String)
    severity = Column(Integer)
