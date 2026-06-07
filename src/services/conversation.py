"""
Conversational Onboarding Engine
Claude-powered multi-turn conversation that guides prospects through
account opening, collects KYC data, and handles intent detection.
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from anthropic import Anthropic
from src.config import settings
from src.models.onboarding import OnboardingStage


STAGE_SEQUENCE = [
    OnboardingStage.WELCOME,
    OnboardingStage.PROFILE_COLLECTION,
    OnboardingStage.PRODUCT_SELECTION,
    OnboardingStage.KYC_INITIATION,
    OnboardingStage.DOCUMENT_UPLOAD,
    OnboardingStage.VERIFICATION,
    OnboardingStage.ACCOUNT_SETUP,
    OnboardingStage.COMPLETED,
]

STAGE_PROGRESS = {
    OnboardingStage.WELCOME: 5,
    OnboardingStage.PROFILE_COLLECTION: 20,
    OnboardingStage.PRODUCT_SELECTION: 35,
    OnboardingStage.KYC_INITIATION: 50,
    OnboardingStage.DOCUMENT_UPLOAD: 65,
    OnboardingStage.VERIFICATION: 80,
    OnboardingStage.ACCOUNT_SETUP: 95,
    OnboardingStage.COMPLETED: 100,
    OnboardingStage.ABANDONED: 0,
}

SYSTEM_PROMPT = """You are Arya, a friendly and knowledgeable digital banking assistant for a modern Indian bank.

Your role is to guide customers through the account opening and KYC process in a conversational, empathetic way.

Guidelines:
- Be warm, concise, and professional (max 2-3 sentences per turn)
- Support both English and Hindi/regional languages
- Collect required information naturally through conversation
- Explain why information is needed when asked
- For KYC documents, guide the customer on what to upload and why
- Handle objections patiently (privacy concerns, data safety)
- Never fabricate information about interest rates or fees
- Always confirm collected information before moving forward

Required information to collect (in order):
1. Full Name, Mobile, Email
2. Date of Birth, PAN number
3. Current Address (complete with pincode)
4. Employment type and approximate income
5. Product interest (account type, loan, FD, etc.)
6. KYC document guidance (Aadhaar, PAN, photo)

When you have collected all necessary info for a stage, end your message with:
[STAGE_COMPLETE: <stage_name>]

When you detect the customer wants to stop/exit, end with:
[SESSION_ABANDON]
"""


class ConversationService:

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def get_welcome_message(self, language: str = "en", initial_intent: Optional[str] = None) -> Dict:
        intent_context = f" I see you're interested in {initial_intent}." if initial_intent else ""
        message = (
            f"Hello! I'm Arya, your digital banking assistant.{intent_context} "
            f"I'm here to help you open your account in just a few minutes — completely paperless. "
            f"May I know your name to get started?"
        )
        return {
            "message": message,
            "message_type": "text",
            "options": None,
            "current_stage": OnboardingStage.WELCOME,
            "progress_percent": STAGE_PROGRESS[OnboardingStage.WELCOME],
        }

    def get_product_options(self) -> List[Dict]:
        return [
            {"label": "Savings Account", "value": "savings_account", "description": "High-interest savings with zero balance"},
            {"label": "Salary Account", "value": "salary_account", "description": "Zero-fee account for salaried individuals"},
            {"label": "Personal Loan", "value": "personal_loan", "description": "Instant paperless loan up to ₹25L"},
            {"label": "Fixed Deposit", "value": "fixed_deposit", "description": "Up to 7.5% interest p.a."},
            {"label": "Home Loan", "value": "home_loan", "description": "Competitive rates from 8.5% p.a."},
            {"label": "Credit Card", "value": "credit_card", "description": "5x rewards + airport lounge access"},
        ]

    def get_kyc_guidance_message(self, product: str) -> Dict:
        base_docs = ["Aadhaar card (front & back)", "PAN card", "Recent passport-size photograph"]
        extra = []
        if product in ["home_loan", "personal_loan", "business_loan"]:
            extra = ["Last 3 months salary slips or bank statements"]
        doc_list = "\n".join(f"• {d}" for d in base_docs + extra)
        return {
            "message": (
                f"Great choice! To complete your KYC for {product.replace('_', ' ').title()}, "
                f"I'll need the following documents:\n\n{doc_list}\n\n"
                f"All documents are encrypted and stored securely. Ready to begin?"
            ),
            "message_type": "options",
            "options": [
                {"label": "Yes, I'm ready", "value": "ready_to_upload"},
                {"label": "Tell me more about security", "value": "security_info"},
                {"label": "Do this later", "value": "save_and_exit"},
            ],
        }

    def chat(
        self,
        session_id: str,
        user_message: str,
        conversation_history: List[Dict],
        current_stage: OnboardingStage,
        collected_data: Dict,
        language: str = "en",
    ) -> Tuple[str, Optional[OnboardingStage], Optional[List[Dict]]]:
        """
        Returns: (assistant_reply, new_stage_if_changed, options_if_any)
        """
        if not settings.anthropic_api_key:
            return self._rule_based_response(user_message, current_stage, collected_data), None, None

        context_info = (
            f"\nCurrent stage: {current_stage.value}\n"
            f"Collected so far: {json.dumps(collected_data, indent=2)}\n"
            f"Conversation language preference: {language}\n"
        )

        messages = [{"role": "system", "content": SYSTEM_PROMPT + context_info}]
        messages += conversation_history
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model=settings.ai_model,
                max_tokens=400,
                system=SYSTEM_PROMPT + context_info,
                messages=[m for m in messages if m["role"] in ("user", "assistant")],
            )
            reply = response.content[0].text.strip()

            # Parse stage transitions
            new_stage = None
            options = None

            if "[STAGE_COMPLETE:" in reply:
                import re
                match = re.search(r'\[STAGE_COMPLETE:\s*(\w+)\]', reply)
                if match:
                    stage_name = match.group(1).lower()
                    reply = reply.replace(match.group(0), "").strip()
                    new_stage = self._advance_stage(current_stage)

            if "[SESSION_ABANDON]" in reply:
                reply = reply.replace("[SESSION_ABANDON]", "").strip()
                new_stage = OnboardingStage.ABANDONED

            if current_stage == OnboardingStage.PRODUCT_SELECTION and new_stage is None:
                options = self.get_product_options()

            return reply, new_stage, options

        except Exception as e:
            return self._rule_based_response(user_message, current_stage, collected_data), None, None

    def _advance_stage(self, current: OnboardingStage) -> OnboardingStage:
        try:
            idx = STAGE_SEQUENCE.index(current)
            if idx + 1 < len(STAGE_SEQUENCE):
                return STAGE_SEQUENCE[idx + 1]
        except ValueError:
            pass
        return current

    def _rule_based_response(
        self,
        user_message: str,
        stage: OnboardingStage,
        collected_data: Dict,
    ) -> str:
        msg = user_message.lower()

        if stage == OnboardingStage.WELCOME:
            return (
                "Thank you! Could you please share your mobile number and email address so I can "
                "set up your profile?"
            )
        elif stage == OnboardingStage.PROFILE_COLLECTION:
            return (
                "Got it. Now I'll need your PAN number and date of birth to proceed with KYC. "
                "Please share when ready."
            )
        elif stage == OnboardingStage.PRODUCT_SELECTION:
            return (
                "Which banking product are you interested in? You can choose from: "
                "Savings Account, Personal Loan, Fixed Deposit, Credit Card, Home Loan."
            )
        elif stage == OnboardingStage.KYC_INITIATION:
            return (
                "Let's complete your KYC. I'll need your Aadhaar number for Aadhaar-based e-KYC. "
                "Your data is encrypted and stored securely as per RBI guidelines."
            )
        elif stage == OnboardingStage.DOCUMENT_UPLOAD:
            return (
                "Please upload your Aadhaar card (front and back) and a recent passport-size photograph. "
                "PAN card upload is also required."
            )
        else:
            return "Thank you for your information. We're processing your application. Is there anything else I can help you with?"

    def extract_entities(self, message: str, stage: OnboardingStage) -> Dict[str, Any]:
        """Simple regex-based entity extraction as fallback."""
        import re
        entities = {}

        mobile_match = re.search(r'\b[6-9]\d{9}\b', message)
        if mobile_match:
            entities["mobile"] = mobile_match.group()

        pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', message.upper())
        if pan_match:
            entities["pan_number"] = pan_match.group()

        aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', message)
        if aadhaar_match:
            entities["aadhaar_number"] = aadhaar_match.group().replace(" ", "")

        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
        if email_match:
            entities["email"] = email_match.group()

        pincode_match = re.search(r'\b[1-9][0-9]{5}\b', message)
        if pincode_match:
            entities["pincode"] = pincode_match.group()

        return entities


conversation_service = ConversationService()
