import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.db import get_db
from database.schema import Borrower
from models.credit_model import (
    predict_pd, compute_global_shap, run_fairlearn_audit,
    FEATURE_NAMES, get_model, get_train_data, get_explainer
)

router = APIRouter(prefix="/api/viveka", tags=["VIVEKA"])


class CustomFeaturesRequest(BaseModel):
    features: dict


def _compute_lime(features_dict):
    try:
        from lime import lime_tabular
        model = get_model()
        X_train = get_train_data()

        explainer = lime_tabular.LimeTabularExplainer(
            training_data=X_train.values,
            feature_names=FEATURE_NAMES,
            class_names=['No Default', 'Default'],
            mode='classification',
            random_state=42,
        )
        feat_array = np.array([features_dict[f] for f in FEATURE_NAMES])
        exp = explainer.explain_instance(feat_array, model.predict_proba, num_features=6)
        return [{'feature': f, 'weight': float(w)} for f, w in exp.as_list()]
    except Exception as e:
        return [{'feature': f, 'weight': 0.0} for f in FEATURE_NAMES[:6]]


@router.get("/global-shap")
def global_shap():
    result = compute_global_shap(sample_size=100)
    return result


@router.get("/explain/{borrower_id}")
def explain_borrower(borrower_id: str, db: Session = Depends(get_db)):
    borrower = db.query(Borrower).filter(Borrower.id == borrower_id).first()
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")

    features = {f: getattr(borrower, f) for f in FEATURE_NAMES}
    result = predict_pd(features)

    shap_list = []
    for fname in FEATURE_NAMES:
        sv = result['shap_values'].get(fname, 0)
        shap_list.append({
            'feature': fname,
            'value': features[fname],
            'shap': sv,
            'direction': 'pos' if sv > 0 else 'neg',
        })
    shap_list.sort(key=lambda x: abs(x['shap']), reverse=True)

    lime_exp = _compute_lime(features)

    return {
        'borrower_id': borrower_id,
        'borrower_name': borrower.name,
        'pd_score': result['pd'],
        'base_value': result['base_value'],
        'shap_values': shap_list,
        'adverse_factors': result['top_adverse'][:3],
        'lime_explanation': lime_exp,
    }


@router.get("/fairness-audit")
def fairness_audit(db: Session = Depends(get_db)):
    borrowers = db.query(Borrower).all()

    features_list = []
    genders = []
    districts = []
    y_true = []
    y_pred = []

    model = get_model()

    for b in borrowers:
        feat = {f: getattr(b, f) for f in FEATURE_NAMES}
        features_list.append([feat[f] for f in FEATURE_NAMES])
        genders.append(b.gender)
        districts.append(b.district)
        y_true.append(b.default_flag)

    feat_df = pd.DataFrame(features_list, columns=FEATURE_NAMES)
    preds = model.predict(feat_df)
    y_pred = list(preds)

    gender_result = run_fairlearn_audit(feat_df, y_true, y_pred, genders)

    male_rate = gender_result['by_group'].get('Male', 0)
    female_rate = gender_result['by_group'].get('Female', 0)

    by_district = {}
    for district in set(districts):
        idxs = [i for i, d in enumerate(districts) if d == district]
        if idxs:
            district_preds = [y_pred[i] for i in idxs]
            by_district[district] = float(np.mean(district_preds))

    geo_rates = list(by_district.values())
    geo_dir = min(geo_rates) / max(geo_rates) if max(geo_rates) > 0 else 1.0

    if gender_result['overall_dir'] >= 0.90:
        status = 'PASS'
    elif gender_result['overall_dir'] >= 0.80:
        status = 'WATCH'
    else:
        status = 'FAIL'

    return {
        'overall_dir': gender_result['overall_dir'],
        'by_gender': {
            'male': male_rate,
            'female': female_rate,
            'dir': gender_result['overall_dir'],
        },
        'by_geography': by_district,
        'geo_dir': geo_dir,
        'equalized_odds': gender_result['equalized_odds_diff'],
        'demographic_parity': gender_result['demographic_parity_diff'],
        'status': status,
        'by_group': gender_result['by_group'],
    }


@router.post("/explain-custom")
def explain_custom(req: CustomFeaturesRequest):
    features = {}
    for f in FEATURE_NAMES:
        if f not in req.features:
            raise HTTPException(status_code=400, detail=f"Missing feature: {f}")
        features[f] = float(req.features[f])

    result = predict_pd(features)

    shap_list = []
    for fname in FEATURE_NAMES:
        sv = result['shap_values'].get(fname, 0)
        shap_list.append({
            'feature': fname,
            'value': features[fname],
            'shap': sv,
            'direction': 'pos' if sv > 0 else 'neg',
        })
    shap_list.sort(key=lambda x: abs(x['shap']), reverse=True)

    lime_exp = _compute_lime(features)

    return {
        'pd_score': result['pd'],
        'base_value': result['base_value'],
        'shap_values': shap_list,
        'adverse_factors': result['top_adverse'][:3],
        'lime_explanation': lime_exp,
    }
