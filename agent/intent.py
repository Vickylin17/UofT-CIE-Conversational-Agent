from __future__ import annotations

from pydantic import BaseModel

from config import AppConfig
from guardrails.policies import is_out_of_scope_query, needs_immigration_disclaimer
from llm import LLMClient
from schemas import IntentResult
from text_utils import is_brief_reply, looks_like_booking_request, match_arrival_status, match_student_type, normalize_user_text


class IntentPayload(BaseModel):
    intent: str
    tool_name: str | None = None
    confidence: float = 0.0
    reasoning: str = ""


INTENT_SYSTEM_PROMPT = """
Classify the student's latest message for a University of Toronto CIE assistant.
Valid intents:
- knowledge: informational question answerable from the resource hub documents
- action: request for a checklist, routing help, advising preparation, or event recommendation
- out_of_scope: unrelated to CIE or international student support

Available tool names:
- pre_arrival_checklist
- support_routing
- advising_preparation
- event_recommendation
- appointment_booking

Return strict JSON with keys: intent, tool_name, confidence, reasoning.
""".strip()


class IntentClassifier:
    def __init__(self, config: AppConfig) -> None:
        self.llm = LLMClient(config.llm)

    def classify(self, text: str) -> IntentResult:
        lowered = normalize_user_text(text)
        if is_out_of_scope_query(text):
            return IntentResult(intent="out_of_scope", confidence=0.95, reasoning="Detected unrelated topic.")

        if looks_like_booking_request(lowered):
            return IntentResult(intent="action", tool_name="appointment_booking", confidence=0.92)

        is_location_query = any(
            phrase in lowered
            for phrase in [
                "where can i find",
                "where do i find",
                "find information",
                "information about",
                "looking for information",
                "where is",
                "link to",
                "page for",
            ]
        )
        if is_location_query and any(
            keyword in lowered
            for keyword in [
                "uhip",
                "health insurance",
                "immigration",
                "study permit",
                "visa",
                "events",
                "workshop",
                "session",
                "orientation",
            ]
        ):
            return IntentResult(intent="action", tool_name="support_routing", confidence=0.9)

        if any(keyword in lowered for keyword in ["checklist", "prepare for arrival", "before i arrive"]):
            return IntentResult(intent="action", tool_name="pre_arrival_checklist", confidence=0.8)
        if is_brief_reply(lowered) and (match_arrival_status(lowered) or match_student_type(lowered)):
            return IntentResult(intent="action", tool_name="pre_arrival_checklist", confidence=0.72)
        if (
            "prepare for advising" in lowered
            or "prepare me for advising" in lowered
            or "advising appointment" in lowered
            or ("appointment" in lowered and "advising" in lowered)
            or ("help me prepare" in lowered and ("advising" in lowered or "appointment" in lowered))
        ):
            return IntentResult(intent="action", tool_name="advising_preparation", confidence=0.85)
        if any(
            keyword in lowered
            for keyword in [
                "who should i contact",
                "who do i contact",
                "route me",
                "support service",
                "i need help",
                "help me",
                "need support",
            ]
        ):
            return IntentResult(intent="action", tool_name="support_routing", confidence=0.8)
        if any(
            keyword in lowered
            for keyword in [
                "recommend an event",
                "recommend events",
                "suggest an event",
                "suggest events",
                "what events",
                "which events",
                "what sessions",
                "which sessions",
            ]
        ):
            return IntentResult(intent="action", tool_name="event_recommendation", confidence=0.75)
        if needs_immigration_disclaimer(text):
            return IntentResult(intent="knowledge", confidence=0.65, reasoning="CIE-related immigration question.")

        fallback = IntentPayload(intent="knowledge", tool_name=None, confidence=0.5, reasoning="Heuristic default.")
        payload = self.llm.safe_complete_json(
            system_prompt=INTENT_SYSTEM_PROMPT,
            user_prompt=f"Student message:\n{text}",
            schema=IntentPayload,
            fallback=fallback,
        )
        return IntentResult.model_validate(payload.model_dump())
