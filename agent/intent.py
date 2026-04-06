from __future__ import annotations

from pydantic import BaseModel

from config import AppConfig
from guardrails.policies import is_out_of_scope_query, needs_immigration_disclaimer
from llm import LLMClient
from schemas import IntentResult


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

Return strict JSON with keys: intent, tool_name, confidence, reasoning.
""".strip()


class IntentClassifier:
    def __init__(self, config: AppConfig) -> None:
        self.llm = LLMClient(config.llm)

    def classify(self, text: str) -> IntentResult:
        lowered = text.lower()
        if is_out_of_scope_query(text):
            return IntentResult(intent="out_of_scope", confidence=0.95, reasoning="Detected unrelated topic.")

        if any(keyword in lowered for keyword in ["checklist", "prepare for arrival", "before i arrive"]):
            return IntentResult(intent="action", tool_name="pre_arrival_checklist", confidence=0.8)
        if any(keyword in lowered for keyword in ["advising", "appointment", "prepare for advising"]):
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
        if any(keyword in lowered for keyword in ["event", "workshop", "session", "orientation"]):
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
