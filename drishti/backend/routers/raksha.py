from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database.db import get_db
from database.schema import ModelRegistry, CompliancePrinciple, PSIHistory
from models.mrm_engine import compute_tier_score
from datetime import date, datetime

router = APIRouter(prefix="/api/raksha", tags=["RAKSHA"])


def model_to_dict(m: ModelRegistry):
    return {
        'id': m.id,
        'name': m.name,
        'model_type': m.model_type,
        'purpose': m.purpose,
        'owner': m.owner,
        'tier': m.tier,
        'status': m.status,
        'validation_status': m.validation_status,
        'last_validated': m.last_validated,
        'psi_current': m.psi_current,
        'gini': m.gini,
        'auc': m.auc,
        'use_scope': m.use_scope,
        'notes': m.notes,
    }


def psi_status(psi):
    if psi is None:
        return 'GREEN'
    if psi >= 0.25:
        return 'RED'
    elif psi >= 0.10:
        return 'AMBER'
    return 'GREEN'


@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    models = db.query(ModelRegistry).all()
    result = []
    for m in models:
        d = model_to_dict(m)
        d['psi_status'] = psi_status(m.psi_current)
        result.append(d)
    return {'models': result}


@router.get("/inventory/{model_id}")
def get_model_detail(model_id: str, db: Session = Depends(get_db)):
    m = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    d = model_to_dict(m)
    d['psi_status'] = psi_status(m.psi_current)

    psi_hist = db.query(PSIHistory).filter(PSIHistory.model_id == model_id).all()
    d['psi_history'] = [{'month': p.month, 'psi': p.psi_value} for p in psi_hist]

    return d


class TierScoreRequest(BaseModel):
    financial_materiality: int
    regulatory_nexus: bool
    complexity: int
    population_size: int


@router.post("/tier-score")
def tier_score(req: TierScoreRequest):
    return compute_tier_score(
        req.financial_materiality,
        req.regulatory_nexus,
        req.complexity,
        req.population_size,
    )


@router.get("/compliance-scorecard")
def compliance_scorecard(db: Session = Depends(get_db)):
    principles = db.query(CompliancePrinciple).all()
    p_list = [{'id': p.id, 'name': p.name, 'status': p.status,
               'score': p.score, 'gap': p.gap} for p in principles]

    scores = [p.score for p in principles]
    overall = sum(scores) / len(scores) if scores else 0

    if overall >= 70:
        overall_status = 'COMPLIANT'
    elif overall >= 40:
        overall_status = 'PARTIAL'
    else:
        overall_status = 'NON-COMPLIANT'

    non_compliant = [p for p in principles if p.status == 'NON-COMPLIANT']
    top_gaps = [f"{p.id}: {p.name}" for p in non_compliant[:3]]

    return {
        'overall_score': round(overall, 1),
        'overall_status': overall_status,
        'principles': p_list,
        'top_gaps': top_gaps,
    }


@router.get("/validation-queue")
def validation_queue(db: Session = Depends(get_db)):
    models = db.query(ModelRegistry).all()

    overdue = []
    due_soon = []
    scheduled = []
    completed = []

    today = date.today()

    for m in models:
        if m.validation_status in ('Validation Overdue', 'Not Validated'):
            days_overdue = None
            if m.last_validated:
                try:
                    lv = datetime.strptime(m.last_validated, '%Y-%m-%d').date()
                    days_overdue = (today - lv).days
                except Exception:
                    days_overdue = 365
            overdue.append({**model_to_dict(m), 'days_overdue': days_overdue, 'psi_status': psi_status(m.psi_current)})
        elif m.validation_status == 'Pending Revalidation':
            due_soon.append({**model_to_dict(m), 'psi_status': psi_status(m.psi_current)})
        elif m.validation_status == 'Validated':
            completed.append({**model_to_dict(m), 'psi_status': psi_status(m.psi_current)})
        else:
            scheduled.append({**model_to_dict(m), 'psi_status': psi_status(m.psi_current)})

    return {
        'overdue': overdue,
        'due_soon': due_soon,
        'scheduled': scheduled,
        'completed': completed,
    }


class StatusUpdateRequest(BaseModel):
    validation_status: str
    notes: Optional[str] = ""


@router.put("/inventory/{model_id}/status")
def update_model_status(model_id: str, req: StatusUpdateRequest, db: Session = Depends(get_db)):
    m = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    m.validation_status = req.validation_status
    m.notes = req.notes or ""
    db.commit()
    return {'success': True, 'model_id': model_id, 'new_status': req.validation_status}


@router.get("/board-summary")
def board_summary(db: Session = Depends(get_db)):
    models = db.query(ModelRegistry).all()
    principles = db.query(CompliancePrinciple).all()

    total = len(models)
    tier1 = sum(1 for m in models if m.tier == 1)
    validated = sum(1 for m in models if m.validation_status == 'Validated')

    scores = [p.score for p in principles]
    avg_compliance = sum(scores) / len(scores) if scores else 0

    critical = sum(1 for m in models if m.psi_current and m.psi_current >= 0.25)
    critical += sum(1 for m in models if m.validation_status in ('Validation Overdue', 'Not Validated'))

    return {
        'total_models': total,
        'tier1_count': tier1,
        'compliant_count': validated,
        'critical_findings': critical,
        'avg_compliance_score': round(avg_compliance, 1),
    }
