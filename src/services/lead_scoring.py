"""
Lead Scoring Engine
Computes a 0-100 score for each lead based on behavioral, demographic,
and engagement signals. Scores drive hot/warm/cold segmentation and
determine priority queue ordering.
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime
from src.models.lead import Lead, LeadQuality
from src.config import settings


SCORE_WEIGHTS = {
    "has_email": 5,
    "has_pan": 10,
    "complete_address": 5,
    "high_income": 15,
    "medium_income": 8,
    "salaried": 10,
    "self_employed": 7,
    "has_specific_product_interest": 10,
    "has_loan_amount": 8,
    "referral_source": 12,
    "branch_walkin": 10,
    "digital_campaign": 5,
    "recent_engagement": 10,
    "multiple_touchpoints": 8,
    "metro_city": 5,
    "credit_score_750_plus": 12,
    "credit_score_700_750": 8,
    "existing_bank_customer": 15,
}


class LeadScoringService:

    def compute_score(self, lead: Lead, extra_signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        score = 0
        breakdown = {}

        # Completeness signals
        if lead.email:
            score += SCORE_WEIGHTS["has_email"]
            breakdown["has_email"] = SCORE_WEIGHTS["has_email"]

        # Product interest
        if lead.interested_product:
            score += SCORE_WEIGHTS["has_specific_product_interest"]
            breakdown["product_interest"] = SCORE_WEIGHTS["has_specific_product_interest"]

        if lead.interested_amount and lead.interested_amount > 0:
            score += SCORE_WEIGHTS["has_loan_amount"]
            breakdown["loan_amount_provided"] = SCORE_WEIGHTS["has_loan_amount"]

        # Source-based scoring
        source_map = {
            "referral": "referral_source",
            "branch_walk_in": "branch_walkin",
            "digital_campaign": "digital_campaign",
        }
        source_key = source_map.get(str(lead.source), None) if lead.source else None
        if source_key:
            score += SCORE_WEIGHTS[source_key]
            breakdown[f"source_{source_key}"] = SCORE_WEIGHTS[source_key]

        # Engagement
        if lead.engagement_count and lead.engagement_count >= 3:
            score += SCORE_WEIGHTS["multiple_touchpoints"]
            breakdown["multiple_touchpoints"] = SCORE_WEIGHTS["multiple_touchpoints"]

        if lead.last_contact_date:
            days_since = (datetime.utcnow() - lead.last_contact_date).days
            if days_since <= 7:
                score += SCORE_WEIGHTS["recent_engagement"]
                breakdown["recent_engagement"] = SCORE_WEIGHTS["recent_engagement"]

        # Extra signals (from caller context or form data)
        if extra_signals:
            income = extra_signals.get("annual_income")
            if income:
                if income >= 1_000_000:  # 10 lakhs+
                    score += SCORE_WEIGHTS["high_income"]
                    breakdown["high_income"] = SCORE_WEIGHTS["high_income"]
                elif income >= 300_000:  # 3-10 lakhs
                    score += SCORE_WEIGHTS["medium_income"]
                    breakdown["medium_income"] = SCORE_WEIGHTS["medium_income"]

            if extra_signals.get("employment_type") == "salaried":
                score += SCORE_WEIGHTS["salaried"]
                breakdown["salaried"] = SCORE_WEIGHTS["salaried"]
            elif extra_signals.get("employment_type") == "self_employed":
                score += SCORE_WEIGHTS["self_employed"]
                breakdown["self_employed"] = SCORE_WEIGHTS["self_employed"]

            credit_score = extra_signals.get("credit_score")
            if credit_score:
                if credit_score >= 750:
                    score += SCORE_WEIGHTS["credit_score_750_plus"]
                    breakdown["credit_score_750_plus"] = SCORE_WEIGHTS["credit_score_750_plus"]
                elif credit_score >= 700:
                    score += SCORE_WEIGHTS["credit_score_700_750"]
                    breakdown["credit_score_700_750"] = SCORE_WEIGHTS["credit_score_700_750"]

            if extra_signals.get("existing_customer"):
                score += SCORE_WEIGHTS["existing_bank_customer"]
                breakdown["existing_bank_customer"] = SCORE_WEIGHTS["existing_bank_customer"]

            metro_cities = ["mumbai", "delhi", "bangalore", "hyderabad", "chennai", "kolkata", "pune"]
            city = (extra_signals.get("city") or "").lower()
            if city in metro_cities:
                score += SCORE_WEIGHTS["metro_city"]
                breakdown["metro_city"] = SCORE_WEIGHTS["metro_city"]

        final_score = min(score, 100)
        quality = self._classify_quality(final_score)

        return {
            "score": final_score,
            "quality": quality,
            "breakdown": breakdown,
        }

    def _classify_quality(self, score: int) -> LeadQuality:
        if score >= settings.lead_score_hot:
            return LeadQuality.HOT
        elif score >= settings.lead_score_warm:
            return LeadQuality.WARM
        return LeadQuality.COLD

    def detect_persona_tags(self, lead: Lead, extra: Optional[Dict] = None) -> list:
        tags = []
        extra = extra or {}

        age = extra.get("age")
        if age:
            if age < 30:
                tags.append("young_professional")
            elif age > 55:
                tags.append("senior_citizen")

        income = extra.get("annual_income", 0) or 0
        if income >= 5_000_000:
            tags.append("hni")
        elif income >= 1_000_000:
            tags.append("affluent")

        if extra.get("employment_type") == "self_employed":
            tags.append("business_owner")

        if lead.source and str(lead.source) == "referral":
            tags.append("referred")

        if lead.interested_product:
            product = lead.interested_product.lower()
            if "loan" in product or "credit" in product:
                tags.append("credit_seeker")
            elif "savings" in product or "account" in product:
                tags.append("savings_focused")
            elif "investment" in product or "fd" in product or "mf" in product:
                tags.append("investor")

        return tags


lead_scoring_service = LeadScoringService()
