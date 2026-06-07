"""
AI Personalization Engine
Uses Claude to generate hyper-personalised product recommendations,
engagement messages, and next-best-action guidance per customer profile.
"""
import json
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from src.config import settings


PRODUCT_CATALOG = {
    "savings_account": {
        "name": "Premium Savings Account",
        "description": "High-interest savings with zero balance option",
        "target_segments": ["young_professional", "savings_focused"],
        "min_income": 0,
    },
    "salary_account": {
        "name": "Salary Account",
        "description": "Zero-fee account with instant salary credits",
        "target_segments": ["young_professional", "salaried"],
        "min_income": 180_000,
    },
    "home_loan": {
        "name": "Home Loan",
        "description": "Competitive rates from 8.5% p.a.",
        "target_segments": ["affluent", "hni", "credit_seeker"],
        "min_income": 300_000,
    },
    "personal_loan": {
        "name": "Instant Personal Loan",
        "description": "Paperless loan up to ₹25 Lakhs in 24 hours",
        "target_segments": ["young_professional", "credit_seeker"],
        "min_income": 200_000,
    },
    "business_loan": {
        "name": "Business Loan / MSME Credit",
        "description": "Collateral-free business loans up to ₹50 Lakhs",
        "target_segments": ["business_owner"],
        "min_income": 0,
    },
    "fixed_deposit": {
        "name": "Fixed Deposit",
        "description": "Up to 7.5% interest p.a. with flexible tenures",
        "target_segments": ["senior_citizen", "investor", "savings_focused"],
        "min_income": 0,
    },
    "mutual_fund": {
        "name": "Mutual Fund Investment",
        "description": "Curated SIP and lump-sum portfolios",
        "target_segments": ["investor", "affluent", "hni"],
        "min_income": 500_000,
    },
    "credit_card": {
        "name": "Rewards Credit Card",
        "description": "5x reward points on spends + airport lounge access",
        "target_segments": ["young_professional", "affluent"],
        "min_income": 300_000,
    },
    "senior_citizen_fd": {
        "name": "Senior Citizen FD",
        "description": "Extra 0.5% interest for senior citizens",
        "target_segments": ["senior_citizen"],
        "min_income": 0,
    },
}


class PersonalizationService:

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def recommend_products(self, persona_tags: List[str], income: float = 0) -> List[Dict]:
        recommendations = []
        for pid, product in PRODUCT_CATALOG.items():
            tag_match = any(t in persona_tags for t in product["target_segments"])
            income_ok = income >= product["min_income"]
            if tag_match or income_ok:
                score = sum(1 for t in persona_tags if t in product["target_segments"])
                recommendations.append({**product, "product_id": pid, "relevance_score": score})

        recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
        return recommendations[:4]

    def generate_personalised_message(
        self,
        customer_name: str,
        persona_tags: List[str],
        recommended_products: List[Dict],
        language: str = "en",
        intent: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> str:
        if not settings.anthropic_api_key:
            return self._fallback_message(customer_name, persona_tags, recommended_products)

        persona_desc = ", ".join(persona_tags) if persona_tags else "general customer"
        products_list = ", ".join(p["name"] for p in recommended_products[:2])

        prompt = f"""You are a friendly and knowledgeable bank relationship manager.
Write a short, personalised greeting message (2-3 sentences max) for a customer with the following profile:

Name: {customer_name}
Customer persona: {persona_desc}
Most relevant products: {products_list}
Language: {language}
Current intent: {intent or "general inquiry"}

Rules:
- Be warm, concise, and professional
- Mention one specific benefit relevant to their profile
- Do not use generic phrases like "valued customer"
- Do not include any disclaimers or legal text
- Write in {language} language (if not English, keep banking terms in English)
"""
        try:
            response = self.client.messages.create(
                model=settings.ai_model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception:
            return self._fallback_message(customer_name, persona_tags, recommended_products)

    def _fallback_message(self, name: str, tags: List[str], products: List[Dict]) -> str:
        product_name = products[0]["name"] if products else "our banking services"
        return (
            f"Hello {name}, welcome! Based on your profile, we think our {product_name} "
            f"would be a great fit for your financial goals. Let's get you started today."
        )

    def determine_next_best_action(
        self,
        lead_score: int,
        persona_tags: List[str],
        engagement_count: int,
        last_contact_days: Optional[int] = None,
    ) -> Dict[str, str]:
        if lead_score >= 75:
            return {
                "action": "direct_call",
                "channel": "phone",
                "message": "High-intent lead — assign to RM for immediate call",
                "priority": "high",
            }
        elif lead_score >= 50:
            if engagement_count == 0:
                return {
                    "action": "send_whatsapp",
                    "channel": "whatsapp",
                    "message": "Warm lead — send personalised WhatsApp with product brochure",
                    "priority": "medium",
                }
            return {
                "action": "email_nurture",
                "channel": "email",
                "message": "Warm lead with engagement — send personalised email offer",
                "priority": "medium",
            }
        else:
            return {
                "action": "drip_campaign",
                "channel": "email_sms",
                "message": "Cold lead — add to 30-day nurture drip campaign",
                "priority": "low",
            }

    def detect_engagement_channel(self, persona_tags: List[str], preferred_channel: Optional[str]) -> str:
        if preferred_channel:
            return preferred_channel
        if "senior_citizen" in persona_tags:
            return "phone"
        if "young_professional" in persona_tags:
            return "whatsapp"
        return "email"


personalization_service = PersonalizationService()
