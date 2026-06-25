import numpy as np
import pandas as pd
import joblib
import os
import shap
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'credit_model.joblib')
EXPLAINER_PATH = os.path.join(os.path.dirname(__file__), 'shap_explainer.joblib')
TRAIN_DATA_PATH = os.path.join(os.path.dirname(__file__), 'train_data.joblib')

FEATURE_NAMES = [
    'dscr', 'current_ratio', 'tol_tnw', 'cmr_score', 'vintage_years',
    'collateral_pct', 'gst_compliance', 'upi_txn_drop', 'sector_stress', 'bureau_dpd'
]

_model = None
_explainer = None
_X_train = None
_X_test = None
_y_test = None


def generate_training_data(n=500):
    np.random.seed(42)
    sector_stress_vals = np.random.uniform(0.0, 1.0, n)
    cmr = np.random.choice([1, 2, 3, 4, 5, 6, 7, 8], n,
                           p=[0.05, 0.10, 0.15, 0.20, 0.20, 0.15, 0.10, 0.05])
    dscr = np.random.uniform(0.3, 2.5, n)
    bureau_dpd = np.random.choice([0, 30, 60, 90], n, p=[0.60, 0.20, 0.12, 0.08])

    X = pd.DataFrame({
        'dscr': dscr,
        'current_ratio': np.random.uniform(0.8, 2.8, n),
        'tol_tnw': np.random.uniform(0.2, 4.0, n),
        'cmr_score': cmr.astype(float),
        'vintage_years': np.random.uniform(1, 25, n),
        'collateral_pct': np.random.uniform(60, 150, n),
        'gst_compliance': np.random.uniform(0.4, 1.0, n),
        'upi_txn_drop': np.random.uniform(-0.5, 0.3, n),
        'sector_stress': sector_stress_vals,
        'bureau_dpd': bureau_dpd.astype(float),
    })

    default_prob = np.zeros(n)
    default_prob += 0.08
    default_prob += np.where(dscr < 1.1, 0.28, 0)
    default_prob += np.where(cmr > 5, 0.22, 0)
    default_prob += np.where(bureau_dpd > 30, 0.32, 0)
    default_prob += sector_stress_vals * 0.12
    default_prob = np.clip(default_prob, 0.02, 0.95)

    y = (np.random.random(n) < default_prob).astype(int)

    return X, y


def train_model():
    global _model, _explainer, _X_train, _X_test, _y_test

    print("Training XGBoost credit model...")
    X, y = generate_training_data(500)
    _X_train, _X_test, y_train, _y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    _model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        eval_metric='logloss',
        verbosity=0,
    )
    _model.fit(_X_train, y_train)

    _explainer = shap.TreeExplainer(_model)

    joblib.dump(_model, MODEL_PATH)
    joblib.dump(_explainer, EXPLAINER_PATH)
    joblib.dump({'X_train': _X_train, 'X_test': _X_test, 'y_test': _y_test}, TRAIN_DATA_PATH)
    print("Model trained and saved.")


def load_model():
    global _model, _explainer, _X_train, _X_test, _y_test

    if os.path.exists(MODEL_PATH):
        _model = joblib.load(MODEL_PATH)
        _explainer = joblib.load(EXPLAINER_PATH)
        data = joblib.load(TRAIN_DATA_PATH)
        _X_train = data['X_train']
        _X_test = data['X_test']
        _y_test = data['y_test']
    else:
        train_model()


def get_model():
    global _model
    if _model is None:
        load_model()
    return _model


def get_explainer():
    global _explainer
    if _explainer is None:
        load_model()
    return _explainer


def get_train_data():
    global _X_train
    if _X_train is None:
        load_model()
    return _X_train


def predict_pd(features: dict) -> dict:
    model = get_model()
    explainer = get_explainer()

    feat_array = np.array([[features[f] for f in FEATURE_NAMES]])
    feat_df = pd.DataFrame(feat_array, columns=FEATURE_NAMES)

    pd_score = float(model.predict_proba(feat_df)[0][1])
    shap_vals = explainer.shap_values(feat_df)

    if isinstance(shap_vals, list):
        sv = shap_vals[1][0]
    else:
        sv = shap_vals[0]

    shap_dict = {}
    for i, fname in enumerate(FEATURE_NAMES):
        shap_dict[fname] = float(sv[i])

    sorted_shap = sorted(shap_dict.items(), key=lambda x: x[1], reverse=True)
    top_adverse = [f for f, v in sorted_shap if v > 0][:3]

    return {
        'pd': pd_score,
        'shap_values': shap_dict,
        'base_value': float(explainer.expected_value if not isinstance(explainer.expected_value, list) else explainer.expected_value[1]),
        'top_adverse': top_adverse,
    }


def compute_global_shap(sample_size=100) -> dict:
    model = get_model()
    explainer = get_explainer()
    X_train = get_train_data()

    sample = X_train.sample(min(sample_size, len(X_train)), random_state=42)
    shap_vals = explainer.shap_values(sample)

    if isinstance(shap_vals, list):
        sv = shap_vals[1]
    else:
        sv = shap_vals

    mean_abs_shap = np.abs(sv).mean(axis=0)
    feature_importance = {FEATURE_NAMES[i]: float(mean_abs_shap[i]) for i in range(len(FEATURE_NAMES))}
    sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

    return {
        'feature_importance': feature_importance,
        'shap_summary': [{'feature': f, 'mean_abs_shap': v} for f, v in sorted_importance],
    }


def run_fairlearn_audit(X_portfolio, y_true, y_pred, sensitive_feature_values):
    from fairlearn.metrics import MetricFrame, demographic_parity_difference, equalized_odds_difference, selection_rate

    sf = np.array(sensitive_feature_values)

    mf = MetricFrame(
        metrics={'selection_rate': selection_rate},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sf,
    )

    by_group = {str(k): float(v['selection_rate']) for k, v in mf.by_group.iterrows()}

    groups = list(by_group.keys())
    rates = list(by_group.values())

    if len(rates) >= 2:
        min_rate = min(rates)
        max_rate = max(rates)
        overall_dir = min_rate / max_rate if max_rate > 0 else 1.0
    else:
        overall_dir = 1.0

    dp_diff = float(demographic_parity_difference(y_true, y_pred, sensitive_features=sf))

    try:
        eo_diff = float(equalized_odds_difference(y_true, y_pred, sensitive_features=sf))
    except Exception:
        eo_diff = 0.0

    if overall_dir >= 0.90:
        status = 'PASS'
    elif overall_dir >= 0.80:
        status = 'WATCH'
    else:
        status = 'FAIL'

    return {
        'overall_dir': overall_dir,
        'by_group': by_group,
        'demographic_parity_diff': dp_diff,
        'equalized_odds_diff': eo_diff,
        'status': status,
    }
