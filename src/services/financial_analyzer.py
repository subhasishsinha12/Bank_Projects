"""
Financial Analyzer
Parses raw AA bank-statement data (ReBIT schema) and computes
aggregated metrics for credit pre-assessment and income verification.

Follows DPDP data minimisation: stores only aggregates, never raw transactions.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


SALARY_NARRATION_PATTERNS = [
    r"salary", r"sal\b", r"payroll", r"wages", r"stipend",
    r"remuneration", r"pay credit", r"ctc", r"basic pay",
]

EMI_NARRATION_PATTERNS = [
    r"emi", r"loan emi", r"instalment", r"equated monthly",
    r"ecs.*loan", r"nach.*loan", r"auto.*debit.*loan",
    r"home loan", r"car loan", r"personal loan",
]

RENT_NARRATION_PATTERNS = [r"rent", r"rental", r"house rent", r"pg rent", r"accommodation"]


class FinancialAnalyzer:

    def analyze(self, fi_data: List[Dict]) -> Dict[str, Any]:
        """
        Entry point: accepts decrypted FI data list (one entry per FIP).
        Returns a FinancialSummary-compatible dict.
        """
        all_accounts = []
        all_transactions = []

        for fip_data in fi_data:
            fip_id = fip_data.get("fipID", "UNKNOWN")
            for account in fip_data.get("data", []):
                summary = account.get("Summary", {})
                txns = account.get("Transactions", {}).get("Transaction", [])
                all_accounts.append({
                    "fip_id": fip_id,
                    "masked_account": account.get("maskedAccNumber"),
                    "account_type": summary.get("type"),
                    "current_balance": self._parse_float(summary.get("currentBalance", "0")),
                    "opening_date": summary.get("openingDate"),
                    "status": summary.get("status"),
                })
                for t in txns:
                    all_transactions.append({**t, "fip_id": fip_id,
                                             "masked_account": account.get("maskedAccNumber")})

        return {
            "accounts": all_accounts,
            **self._income_analysis(all_transactions),
            **self._balance_analysis(all_accounts, all_transactions),
            **self._obligation_analysis(all_transactions),
            **self._credit_behaviour(all_transactions),
            **self._pre_approval_limits(all_transactions),
        }

    # ------------------------------------------------------------------ #
    # Income Analysis
    # ------------------------------------------------------------------ #

    def _income_analysis(self, transactions: List[Dict]) -> Dict:
        monthly_salary: Dict[str, List[float]] = defaultdict(list)
        employer_hits: Dict[str, int] = defaultdict(int)

        for t in transactions:
            if t.get("type") != "CREDIT":
                continue
            narr = (t.get("narration") or "").lower()
            if any(re.search(p, narr) for p in SALARY_NARRATION_PATTERNS):
                amount = self._parse_float(t.get("amount", "0"))
                if amount < 5_000:  # ignore noise
                    continue
                month_key = t.get("valueDate", "")[:7]    # YYYY-MM
                monthly_salary[month_key].append(amount)

                # Extract employer name heuristic
                words = narr.upper().split()
                for kw in ["SALARY", "SAL", "PAYROLL"]:
                    if kw in words:
                        idx = words.index(kw)
                        if idx + 1 < len(words):
                            employer_hits[words[idx + 1]] += 1

        if not monthly_salary:
            return {
                "verified_monthly_income": 0,
                "income_confidence": 0.0,
                "employer_verified": False,
                "employer_name_aa": None,
            }

        monthly_totals = [sum(v) for v in monthly_salary.values()]
        median_income = sorted(monthly_totals)[len(monthly_totals) // 2]
        consistency   = len(monthly_salary) / max(6, len(monthly_salary))   # months with salary / expected
        confidence    = min(round(consistency * 0.9, 2), 0.99)

        top_employer = max(employer_hits, key=employer_hits.get) if employer_hits else None

        return {
            "verified_monthly_income": round(median_income, 2),
            "income_confidence": confidence,
            "employer_verified": top_employer is not None,
            "employer_name_aa": top_employer,
        }

    # ------------------------------------------------------------------ #
    # Balance Analysis
    # ------------------------------------------------------------------ #

    def _balance_analysis(self, accounts: List[Dict], transactions: List[Dict]) -> Dict:
        if not accounts:
            return {"avg_monthly_balance": 0, "min_monthly_balance_6m": 0,
                    "max_monthly_balance_6m": 0, "total_accounts_found": 0,
                    "total_fips_linked": 0}

        balances_by_month: Dict[str, List[float]] = defaultdict(list)
        for t in transactions:
            bal = self._parse_float(t.get("currentBalance", "0"))
            month = t.get("valueDate", "")[:7]
            if month and bal > 0:
                balances_by_month[month].append(bal)

        monthly_avgs = [sum(v) / len(v) for v in balances_by_month.values() if v]

        return {
            "avg_monthly_balance": round(sum(monthly_avgs) / len(monthly_avgs), 2) if monthly_avgs else 0,
            "min_monthly_balance_6m": round(min(monthly_avgs), 2) if monthly_avgs else 0,
            "max_monthly_balance_6m": round(max(monthly_avgs), 2) if monthly_avgs else 0,
            "total_accounts_found": len(accounts),
            "total_fips_linked": len({a["fip_id"] for a in accounts}),
        }

    # ------------------------------------------------------------------ #
    # Obligation (EMI / Debt) Analysis
    # ------------------------------------------------------------------ #

    def _obligation_analysis(self, transactions: List[Dict]) -> Dict:
        monthly_obligations: Dict[str, float] = defaultdict(float)
        obligation_sources: Dict[str, float] = {}   # narration → typical amount

        for t in transactions:
            if t.get("type") != "DEBIT":
                continue
            narr = (t.get("narration") or "").lower()
            if any(re.search(p, narr) for p in EMI_NARRATION_PATTERNS):
                amount = self._parse_float(t.get("amount", "0"))
                month  = t.get("valueDate", "")[:7]
                monthly_obligations[month] += amount
                key = narr[:40]
                if key not in obligation_sources:
                    obligation_sources[key] = amount

        if not monthly_obligations:
            return {"total_monthly_obligations": 0, "obligation_count": 0,
                    "debt_to_income_ratio": 0}

        avg_obligations = sum(monthly_obligations.values()) / len(monthly_obligations)
        return {
            "total_monthly_obligations": round(avg_obligations, 2),
            "obligation_count": len(obligation_sources),
            "debt_to_income_ratio": 0,   # computed after income is known
        }

    # ------------------------------------------------------------------ #
    # Credit Behaviour
    # ------------------------------------------------------------------ #

    def _credit_behaviour(self, transactions: List[Dict]) -> Dict:
        bounced = 0
        returned_emi = 0
        for t in transactions:
            narr = (t.get("narration") or "").lower()
            if "bounce" in narr or "dishonour" in narr or "return" in narr:
                if any(re.search(p, narr) for p in EMI_NARRATION_PATTERNS):
                    returned_emi += 1
                else:
                    bounced += 1

        # Simple credit behaviour score: start 100, deduct for negatives
        score = 100 - (bounced * 5) - (returned_emi * 10)
        return {
            "bounced_cheques_6m": bounced,
            "returned_emi_count_6m": returned_emi,
            "credit_behaviour_score": max(0, min(100, score)),
        }

    # ------------------------------------------------------------------ #
    # Pre-approval Limits
    # ------------------------------------------------------------------ #

    def _pre_approval_limits(self, transactions: List[Dict]) -> Dict:
        income_data  = self._income_analysis(transactions)
        monthly_income = income_data.get("verified_monthly_income", 0)
        annual_income  = monthly_income * 12

        obligation_data = self._obligation_analysis(transactions)
        obligations = obligation_data.get("total_monthly_obligations", 0)
        dti = (obligations / monthly_income) if monthly_income > 0 else 1.0

        # Conservative pre-approval rules (typical bank credit policy)
        available_emi_capacity = max(0, monthly_income * 0.5 - obligations)

        # Personal Loan: EMI = 3% of loan amount (approx 36m @ 12%)
        personal_loan = round(available_emi_capacity / 0.03 / 100000, 1) * 100000 if dti < 0.7 else 0

        # Credit Card: 3x monthly income, capped at 5L for new customers
        credit_card = min(monthly_income * 3, 500_000) if monthly_income > 20_000 else 0

        # Home Loan: 60x monthly income (typical 20yr @ 8.5%)
        home_loan = round(monthly_income * 60 / 100000, 1) * 100000 if monthly_income > 30_000 and dti < 0.6 else 0

        return {
            "pre_approved_personal_loan": personal_loan,
            "pre_approved_credit_card": credit_card,
            "pre_approved_home_loan": home_loan,
            "debt_to_income_ratio": round(dti, 3),
        }

    def compute_dti(self, income: float, obligations: float) -> float:
        return round(obligations / income, 3) if income > 0 else 1.0

    def format_for_db(self, analysis: Dict, customer_id: str, aa_consent_id: str) -> Dict:
        """Convert analysis dict into FinancialSummary model kwargs."""
        dti = self.compute_dti(
            analysis.get("verified_monthly_income", 0),
            analysis.get("total_monthly_obligations", 0),
        )
        now = datetime.utcnow()
        return {
            "customer_id": customer_id,
            "verified_monthly_income": analysis.get("verified_monthly_income"),
            "income_confidence": analysis.get("income_confidence"),
            "employer_verified": analysis.get("employer_verified"),
            "employer_name_aa": analysis.get("employer_name_aa"),
            "avg_monthly_balance": analysis.get("avg_monthly_balance"),
            "min_monthly_balance_6m": analysis.get("min_monthly_balance_6m"),
            "max_monthly_balance_6m": analysis.get("max_monthly_balance_6m"),
            "total_monthly_obligations": analysis.get("total_monthly_obligations"),
            "obligation_count": analysis.get("obligation_count"),
            "debt_to_income_ratio": dti,
            "total_accounts_found": analysis.get("total_accounts_found"),
            "total_fips_linked": analysis.get("total_fips_linked"),
            "pre_approved_personal_loan": analysis.get("pre_approved_personal_loan"),
            "pre_approved_credit_card": analysis.get("pre_approved_credit_card"),
            "pre_approved_home_loan": analysis.get("pre_approved_home_loan"),
            "credit_behaviour_score": analysis.get("credit_behaviour_score"),
            "bounced_cheques_6m": analysis.get("bounced_cheques_6m"),
            "returned_emi_count_6m": analysis.get("returned_emi_count_6m"),
            "analysis_from": (now - timedelta(days=180)).strftime("%Y-%m-%d"),
            "analysis_to": now.strftime("%Y-%m-%d"),
            "aa_consent_id": aa_consent_id,
        }

    def _parse_float(self, value: Any) -> float:
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0


financial_analyzer = FinancialAnalyzer()
