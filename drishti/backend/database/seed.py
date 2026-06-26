import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from .db import engine, SessionLocal
from .schema import Base, Borrower, ModelRegistry, PSIHistory, CompliancePrinciple, EWSAlert

SECTORS = ['Textile', 'Chemical', 'Diamond', 'Packaging', 'Engineering', 'Pharma']
DISTRICTS = ['Surat', 'Bharuch', 'Navsari', 'Tapi', 'Valsad']
NAMES_M = ['Rajesh Shah', 'Mahesh Patel', 'Suresh Modi', 'Dinesh Joshi', 'Ramesh Desai',
           'Kamlesh Mehta', 'Hitesh Trivedi', 'Nilesh Parikh', 'Alpesh Bhatt', 'Paresh Gandhi',
           'Mukesh Sharma', 'Vimal Agrawal', 'Sanjay Yadav', 'Vijay Kumar', 'Ashok Gupta',
           'Rakesh Verma', 'Prakash Singh', 'Naresh Tiwari', 'Umesh Mishra', 'Ganesh Dubey',
           'Jignesh Solanki', 'Mitesh Chauhan', 'Dipesh Vasava', 'Kalpesh Rathod', 'Yogesh Nayak']
NAMES_F = ['Priya Shah', 'Anjali Patel', 'Rekha Modi', 'Sunita Joshi', 'Meena Desai',
           'Kavita Mehta', 'Geeta Trivedi', 'Seema Parikh', 'Asha Bhatt', 'Usha Gandhi',
           'Nita Sharma', 'Mita Agrawal', 'Savita Yadav', 'Lalita Kumar', 'Sarla Gupta',
           'Poonam Verma', 'Archana Singh', 'Vandana Tiwari', 'Manisha Mishra', 'Sushma Dubey',
           'Heena Solanki', 'Falguni Chauhan', 'Bindiya Vasava', 'Chandrika Rathod', 'Jyoti Nayak']


def generate_borrowers():
    np.random.seed(42)
    borrowers = []

    sector_stress_map = {
        'Textile': 0.65, 'Chemical': 0.35, 'Diamond': 0.70,
        'Packaging': 0.30, 'Engineering': 0.40, 'Pharma': 0.20
    }

    for i in range(50):
        gender = 'Male' if i < 35 else 'Female'
        name = NAMES_M[i % 25] if gender == 'Male' else NAMES_F[i % 25]
        sector = SECTORS[i % 6]
        district = DISTRICTS[i % 5]
        vintage = np.random.uniform(1, 25)
        cmr = np.random.choice([1, 2, 3, 4, 5, 6, 7, 8], p=[0.05, 0.10, 0.15, 0.20, 0.20, 0.15, 0.10, 0.05])
        dscr = np.random.uniform(0.3, 2.5)
        bureau_dpd = np.random.choice([0, 0, 0, 30, 60, 90], p=[0.45, 0.25, 0.10, 0.10, 0.05, 0.05])
        stress = sector_stress_map[sector] + np.random.uniform(-0.1, 0.1)
        stress = np.clip(stress, 0, 1)

        default_prob = 0.1
        if dscr < 1.1:
            default_prob += 0.25
        if cmr > 5:
            default_prob += 0.20
        if bureau_dpd > 30:
            default_prob += 0.30
        if stress > 0.6:
            default_prob += 0.10

        default_flag = 1 if np.random.random() < min(default_prob, 0.95) else 0

        pd_current = min(0.95, max(0.01, default_prob * 0.8 + np.random.uniform(-0.05, 0.05)))

        pd_history = []
        pd_val = pd_current * 0.6
        for m in range(6):
            pd_val = pd_val * (1 + np.random.uniform(-0.05, 0.12))
            pd_val = np.clip(pd_val, 0.01, 0.95)
            pd_history.append(round(float(pd_val), 4))
        pd_history[-1] = round(float(pd_current), 4)

        if pd_current > 0.5 or bureau_dpd >= 60:
            ews_stage = 'RED'
        elif pd_current > 0.25 or bureau_dpd >= 30 or dscr < 1.1:
            ews_stage = 'AMBER'
        else:
            ews_stage = 'GREEN'

        if pd_current > 0.6:
            inas_stage = 'Stage 3'
        elif pd_current > 0.25 or ews_stage == 'RED':
            inas_stage = 'Stage 2'
        else:
            inas_stage = 'Stage 1'

        sicr = inas_stage == 'Stage 2' or (pd_current - pd_history[0]) > 0.10

        risk_drivers = []
        if dscr < 1.1:
            risk_drivers.append('Low DSCR')
        if cmr > 5:
            risk_drivers.append('High CMR Score')
        if bureau_dpd > 0:
            risk_drivers.append(f'Bureau DPD: {bureau_dpd} days')
        if stress > 0.55:
            risk_drivers.append(f'Sector stress ({sector})')
        if not risk_drivers:
            risk_drivers.append('Monitoring: UPI transaction trend')

        borrowers.append({
            'id': f'B{str(i+1).zfill(3)}',
            'name': name,
            'sector': sector,
            'district': district,
            'loan_amount': round(float(np.random.uniform(10, 500)), 1),
            'gender': gender,
            'dscr': round(float(dscr), 3),
            'current_ratio': round(float(np.random.uniform(0.8, 2.8)), 3),
            'tol_tnw': round(float(np.random.uniform(0.2, 4.0)), 3),
            'cmr_score': float(cmr),
            'vintage_years': round(float(vintage), 1),
            'collateral_pct': round(float(np.random.uniform(60, 150)), 1),
            'gst_compliance': round(float(np.random.uniform(0.4, 1.0)), 3),
            'upi_txn_drop': round(float(np.random.uniform(-0.5, 0.3)), 3),
            'sector_stress': round(float(stress), 3),
            'bureau_dpd': float(bureau_dpd),
            'default_flag': default_flag,
            'pd_current': round(float(pd_current), 4),
            'pd_history': pd_history,
            'ews_stage': ews_stage,
            'inas_stage': inas_stage,
            'sicr_alert': bool(sicr),
            'top_risk_drivers': risk_drivers[:3],
        })

    return borrowers


MODELS_DATA = [
    {'id': 'M001', 'name': 'MSME Credit Scorecard v3.2', 'model_type': 'XGBoost',
     'purpose': 'PD estimation for MSME segment', 'owner': 'Credit Risk Analytics',
     'tier': 1, 'status': 'Active', 'validation_status': 'Validated',
     'last_validated': '2025-11-15', 'psi_current': 0.08, 'gini': 0.61, 'auc': 0.82,
     'use_scope': 'MSME loans ₹10L–₹5Cr'},
    {'id': 'M002', 'name': 'Retail Credit Scorecard v2.1', 'model_type': 'Logistic Regression',
     'purpose': 'PD estimation for retail/personal loans', 'owner': 'Retail Risk',
     'tier': 1, 'status': 'Active', 'validation_status': 'Validated',
     'last_validated': '2025-09-20', 'psi_current': 0.15, 'gini': 0.55, 'auc': 0.78,
     'use_scope': 'Personal loans, credit cards'},
    {'id': 'M003', 'name': 'Fraud Detection Model v1.4', 'model_type': 'Random Forest',
     'purpose': 'Transaction-level fraud scoring', 'owner': 'Digital Banking Risk',
     'tier': 1, 'status': 'Active', 'validation_status': 'Pending Revalidation',
     'last_validated': '2024-12-01', 'psi_current': 0.28, 'gini': 0.71, 'auc': 0.88,
     'use_scope': 'All digital transactions'},
    {'id': 'M004', 'name': 'CIBIL Bureau Score (Vendor)', 'model_type': 'Vendor — Opaque',
     'purpose': 'External creditworthiness score', 'owner': 'Credit Policy',
     'tier': 2, 'status': 'Active', 'validation_status': 'Due Diligence Only',
     'last_validated': '2025-06-10', 'psi_current': 0.06, 'gini': None, 'auc': None,
     'use_scope': 'All retail and MSME origination'},
    {'id': 'M005', 'name': 'ECL/IndAS 109 PD Model', 'model_type': 'Logistic Regression + Macro Overlay',
     'purpose': 'IFRS 9 expected credit loss provisioning', 'owner': 'Finance & Accounts Risk',
     'tier': 1, 'status': 'Active', 'validation_status': 'Validated',
     'last_validated': '2025-08-30', 'psi_current': 0.09, 'gini': 0.58, 'auc': 0.79,
     'use_scope': 'ECL provisioning — all segments'},
    {'id': 'M006', 'name': 'AML Transaction Monitoring', 'model_type': 'Rule-Based + ML Overlay',
     'purpose': 'Suspicious transaction detection', 'owner': 'Compliance',
     'tier': 2, 'status': 'Active', 'validation_status': 'Validated',
     'last_validated': '2025-10-15', 'psi_current': 0.14, 'gini': None, 'auc': None,
     'use_scope': 'AML/CFT compliance screening'},
    {'id': 'M007', 'name': 'ICAAP Stress Test Model', 'model_type': 'Macroeconomic Satellite',
     'purpose': 'Capital adequacy under stress scenarios', 'owner': 'Risk Management',
     'tier': 1, 'status': 'Active', 'validation_status': 'Validation Overdue',
     'last_validated': '2024-06-30', 'psi_current': 0.31, 'gini': None, 'auc': None,
     'use_scope': 'ICAAP, RBI stress reporting'},
    {'id': 'M008', 'name': 'Collection Propensity Score', 'model_type': 'XGBoost',
     'purpose': 'NPA recovery prioritisation', 'owner': 'Recovery & Collections',
     'tier': 3, 'status': 'Active', 'validation_status': 'Not Validated',
     'last_validated': None, 'psi_current': 0.22, 'gini': 0.44, 'auc': 0.71,
     'use_scope': 'NPA accounts prioritisation'},
]

PSI_HISTORY_DATA = {
    'M001': [0.05, 0.06, 0.07, 0.08, 0.09, 0.08],
    'M002': [0.08, 0.10, 0.11, 0.12, 0.14, 0.15],
    'M003': [0.15, 0.18, 0.21, 0.25, 0.27, 0.28],
    'M004': [0.04, 0.05, 0.05, 0.06, 0.06, 0.06],
    'M005': [0.07, 0.07, 0.08, 0.09, 0.09, 0.09],
    'M006': [0.10, 0.11, 0.12, 0.13, 0.13, 0.14],
    'M007': [0.18, 0.22, 0.25, 0.28, 0.30, 0.31],
    'M008': [0.14, 0.16, 0.18, 0.19, 0.21, 0.22],
}

COMPLIANCE_DATA = [
    {'id': 'P1', 'name': 'Governance & Accountability', 'status': 'PARTIAL', 'score': 55,
     'gap': 'MRM policy exists but not Board-approved. CRO accountability not formally documented.'},
    {'id': 'P2', 'name': 'Model Identification & Inventory', 'status': 'PARTIAL', 'score': 45,
     'gap': 'AI/ML models and 3 vendor models not in formal inventory. Excel tools excluded.'},
    {'id': 'P3', 'name': 'Model Development Standards', 'status': 'COMPLIANT', 'score': 72,
     'gap': 'MDD exists for Tier-1 models. AI/ML models lack full development documentation.'},
    {'id': 'P4', 'name': 'Independent Validation', 'status': 'NON-COMPLIANT', 'score': 28,
     'gap': 'No structural validation independence. Validators report to same function as developers. M008 not validated.'},
    {'id': 'P5', 'name': 'Ongoing Monitoring', 'status': 'PARTIAL', 'score': 50,
     'gap': 'Manual PSI monitoring only. No automated alerts. M007 overdue by 12 months.'},
    {'id': 'P6', 'name': 'Third-Party Model Governance', 'status': 'NON-COMPLIANT', 'score': 20,
     'gap': 'CIBIL vendor model: no due diligence documentation, no contractual audit rights, no transition plan.'},
    {'id': 'P7', 'name': 'AI/ML Specific Requirements', 'status': 'NON-COMPLIANT', 'score': 15,
     'gap': 'No XAI (SHAP/LIME) layer deployed. No fairness testing. No adversarial testing. No human oversight protocol for adverse decisions.'},
    {'id': 'P8', 'name': 'Model Risk Appetite & Reporting', 'status': 'NON-COMPLIANT', 'score': 22,
     'gap': 'No quantitative model risk appetite statement. No Board MRM dashboard. No examination kit prepared.'},
]

MONTHS = ['Jan 2026', 'Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026']


def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Borrower).count() > 0:
        db.close()
        return

    print("Seeding demo data...")

    borrowers = generate_borrowers()
    for b in borrowers:
        db.add(Borrower(**b))

    for m in MODELS_DATA:
        db.add(ModelRegistry(**m))

    for model_id, psi_vals in PSI_HISTORY_DATA.items():
        for i, psi in enumerate(psi_vals):
            db.add(PSIHistory(model_id=model_id, month=MONTHS[i], psi_value=psi))

    for c in COMPLIANCE_DATA:
        db.add(CompliancePrinciple(**c))

    red_borrowers = [b for b in borrowers if b['ews_stage'] == 'RED'][:5]
    amber_borrowers = [b for b in borrowers if b['ews_stage'] == 'AMBER'][:3]
    alert_borrowers = red_borrowers + amber_borrowers

    alert_types_red = ['SMA-0 Risk', 'SICR Trigger', 'PD Spike', 'Bureau DPD Alert', 'DSCR Breach']
    alert_types_amber = ['PSI Watch', 'Sector Stress', 'UPI Drop Alert']

    from datetime import datetime, timedelta
    import random
    random.seed(42)

    for i, b in enumerate(red_borrowers):
        db.add(EWSAlert(
            borrower_id=b['id'],
            borrower_name=b['name'],
            alert_type=alert_types_red[i % len(alert_types_red)],
            trigger_reason=b['top_risk_drivers'][0] if b['top_risk_drivers'] else 'Risk threshold breach',
            shap_driver=b['top_risk_drivers'][0] if b['top_risk_drivers'] else 'DSCR decline',
            raised_at=(datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
            severity=1,
        ))

    for i, b in enumerate(amber_borrowers):
        db.add(EWSAlert(
            borrower_id=b['id'],
            borrower_name=b['name'],
            alert_type=alert_types_amber[i % len(alert_types_amber)],
            trigger_reason=b['top_risk_drivers'][0] if b['top_risk_drivers'] else 'Early warning signal',
            shap_driver=b['top_risk_drivers'][0] if b['top_risk_drivers'] else 'Sector stress',
            raised_at=(datetime.now() - timedelta(hours=random.randint(72, 240))).isoformat(),
            severity=2,
        ))

    db.commit()
    db.close()
    print("Seeding complete.")
