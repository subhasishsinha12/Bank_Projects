import numpy as np
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from database.db import get_db
from database.schema import Borrower, PSIHistory, ModelRegistry, EWSAlert
from models.credit_model import predict_pd, FEATURE_NAMES, get_explainer

router = APIRouter(prefix="/api/satya", tags=["SATYA"])


def borrower_to_dict(b: Borrower):
    return {
        'id': b.id,
        'name': b.name,
        'sector': b.sector,
        'district': b.district,
        'loan_amount': b.loan_amount,
        'gender': b.gender,
        'pd_current': b.pd_current,
        'pd_history': b.pd_history,
        'ews_stage': b.ews_stage,
        'inas_stage': b.inas_stage,
        'sicr_alert': b.sicr_alert,
        'top_risk_drivers': b.top_risk_drivers,
        'dscr': b.dscr,
        'cmr_score': b.cmr_score,
        'bureau_dpd': b.bureau_dpd,
        'default_flag': b.default_flag,
    }


@router.get("/portfolio")
def portfolio(
    sector: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    ews: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Borrower)
    if sector:
        q = q.filter(Borrower.sector == sector)
    if stage:
        q = q.filter(Borrower.inas_stage == stage)
    if ews:
        q = q.filter(Borrower.ews_stage == ews)

    borrowers = q.all()
    return {'borrowers': [borrower_to_dict(b) for b in borrowers]}


@router.get("/borrower/{borrower_id}")
def get_borrower(borrower_id: str, db: Session = Depends(get_db)):
    b = db.query(Borrower).filter(Borrower.id == borrower_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Borrower not found")

    features = {f: getattr(b, f) for f in FEATURE_NAMES}
    result = predict_pd(features)

    explainer = get_explainer()
    base_value = float(explainer.expected_value if not isinstance(explainer.expected_value, list) else explainer.expected_value[1])

    shap_pd_change = []
    for fname in FEATURE_NAMES:
        sv = result['shap_values'].get(fname, 0)
        shap_pd_change.append({
            'feature': fname,
            'value': features[fname],
            'contribution': sv,
            'direction': 'pos' if sv > 0 else 'neg',
        })
    shap_pd_change.sort(key=lambda x: abs(x['contribution']), reverse=True)

    d = borrower_to_dict(b)
    d['shap_pd_change'] = shap_pd_change[:6]
    d['ews_score'] = result['pd']
    d['base_value'] = base_value

    return d


@router.get("/psi-monitor")
def psi_monitor(db: Session = Depends(get_db)):
    models = db.query(ModelRegistry).all()
    result = []

    for m in models:
        psi_hist = db.query(PSIHistory).filter(PSIHistory.model_id == m.id).all()
        history = [{'month': p.month, 'psi': p.psi_value} for p in psi_hist]

        if m.psi_current >= 0.25:
            status = 'CRITICAL'
        elif m.psi_current >= 0.10:
            status = 'WATCH'
        else:
            status = 'STABLE'

        result.append({
            'id': m.id,
            'name': m.name,
            'psi_history': history,
            'current_psi': m.psi_current,
            'status': status,
        })

    result.sort(key=lambda x: x['current_psi'], reverse=True)
    return {'models': result}


@router.get("/heatmap")
def heatmap(db: Session = Depends(get_db)):
    borrowers = db.query(Borrower).all()
    sectors = sorted(set(b.sector for b in borrowers))
    stages = ['GREEN', 'AMBER', 'RED']

    matrix = [[0] * len(stages) for _ in range(len(sectors))]
    exposure_matrix = [[0.0] * len(stages) for _ in range(len(sectors))]

    for b in borrowers:
        si = sectors.index(b.sector)
        sti = stages.index(b.ews_stage)
        matrix[si][sti] += 1
        exposure_matrix[si][sti] += b.loan_amount

    total_exposure = sum(b.loan_amount for b in borrowers)
    red_exposure = sum(b.loan_amount for b in borrowers if b.ews_stage == 'RED')

    return {
        'matrix': matrix,
        'exposure_matrix': exposure_matrix,
        'sectors': sectors,
        'stages': stages,
        'total_exposure': round(total_exposure, 1),
        'red_exposure': round(red_exposure, 1),
    }


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(EWSAlert).order_by(EWSAlert.severity, EWSAlert.id.desc()).all()
    return {
        'alerts': [{
            'id': a.id,
            'borrower_id': a.borrower_id,
            'name': a.borrower_name,
            'alert_type': a.alert_type,
            'trigger_reason': a.trigger_reason,
            'shap_driver': a.shap_driver,
            'raised_at': a.raised_at,
            'severity': a.severity,
        } for a in alerts]
    }


@router.get("/portfolio-summary")
def portfolio_summary(db: Session = Depends(get_db)):
    borrowers = db.query(Borrower).all()

    total = len(borrowers)
    red = sum(1 for b in borrowers if b.ews_stage == 'RED')
    amber = sum(1 for b in borrowers if b.ews_stage == 'AMBER')
    green = sum(1 for b in borrowers if b.ews_stage == 'GREEN')
    stage2 = sum(1 for b in borrowers if b.inas_stage == 'Stage 2')
    stage3 = sum(1 for b in borrowers if b.inas_stage == 'Stage 3')
    total_exposure = sum(b.loan_amount for b in borrowers)
    at_risk = sum(b.loan_amount for b in borrowers if b.ews_stage in ('RED', 'AMBER'))
    avg_pd = np.mean([b.pd_current for b in borrowers]) if borrowers else 0

    sector_breakdown = {}
    for b in borrowers:
        if b.sector not in sector_breakdown:
            sector_breakdown[b.sector] = {'count': 0, 'exposure': 0, 'red': 0}
        sector_breakdown[b.sector]['count'] += 1
        sector_breakdown[b.sector]['exposure'] += b.loan_amount
        if b.ews_stage == 'RED':
            sector_breakdown[b.sector]['red'] += 1

    return {
        'total_accounts': total,
        'red_count': red,
        'amber_count': amber,
        'green_count': green,
        'stage2_count': stage2,
        'stage3_count': stage3,
        'total_exposure': round(total_exposure, 1),
        'at_risk_exposure': round(at_risk, 1),
        'avg_pd': round(float(avg_pd), 4),
        'sector_breakdown': sector_breakdown,
    }
