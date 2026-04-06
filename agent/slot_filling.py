from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from config import AppConfig
from llm import LLMClient
from tools.base import ActionTool


class SlotExtractionPayload(BaseModel):
    extracted_params: dict[str, Any] = {}


SLOT_FILLING_SYSTEM_PROMPT = """
Extract tool parameters from the student message.
Return strict JSON with a single key `extracted_params`.
Only include parameters that are explicitly provided or strongly implied.
Use normalized lowercase values for categorical slots.
""".strip()


class SlotFiller:
    def __init__(self, config: AppConfig) -> None:
        self.llm = LLMClient(config.llm)

    def _heuristic_extract(self, tool: ActionTool, text: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        lowered = text.lower()
        existing = existing or {}
        extracted: dict[str, Any] = {}

        if tool.name == "pre_arrival_checklist":
            if "undergrad" in lowered:
                extracted["student_type"] = "undergraduate"
            elif "graduate" in lowered or "masters" in lowered or "phd" in lowered:
                extracted["student_type"] = "graduate"
            elif "exchange" in lowered or "visiting" in lowered:
                extracted["student_type"] = "exchange"
            elif "other" in lowered:
                extracted["student_type"] = "other"

            if "already in canada" in lowered or "i'm in canada" in lowered:
                extracted["arrival_status"] = "already_in_canada"
            elif "arriving soon" in lowered or "next week" in lowered or "this month" in lowered:
                extracted["arrival_status"] = "arriving_soon"
            elif "not arrived" in lowered or "before i arrive" in lowered or "haven't arrived" in lowered:
                extracted["arrival_status"] = "not_arrived"

        elif tool.name == "support_routing":
            extracted["user_query"] = text.strip()

        elif tool.name == "advising_preparation":
            if lowered.strip() in {"high", "medium", "low"}:
                extracted["urgency"] = lowered.strip()
            elif any(token in lowered for token in ["urgent", "asap", "immediately"]):
                extracted["urgency"] = "high"
            elif any(token in lowered for token in ["medium", "soon", "this week"]):
                extracted["urgency"] = "medium"
            elif any(token in lowered for token in ["low", "not urgent", "later"]):
                extracted["urgency"] = "low"

            if "urgency" in existing and "timeline" not in existing:
                extracted["timeline"] = text.strip()
            elif "timeline" in existing and "documents_ready" not in existing:
                extracted["documents_ready"] = text.strip()
            elif "documents_ready" in existing and "goal" not in existing:
                extracted["goal"] = text.strip()
            else:
                cleaned_issue = re.sub(
                    r"\b(help me|prepare me|prepare|for advising|advising appointment|appointment|urgent|asap|immediately|low|medium|high)\b",
                    "",
                    text,
                    flags=re.I,
                )
                cleaned_issue = " ".join(cleaned_issue.split()).strip(" ,.-")
                generic_values = {"", "advising", "immigration", "immigration advising"}
                if cleaned_issue.lower() not in generic_values:
                    extracted["issue"] = cleaned_issue

        elif tool.name == "event_recommendation":
            extracted["topic"] = text.strip()

        return extracted

    def extract(self, tool: ActionTool, text: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        existing = existing or {}
        heuristic = self._heuristic_extract(tool, text, existing=existing)

        tool_description = "\n".join(
            [
                f"Tool name: {tool.name}",
                f"Tool description: {tool.description}",
                "Parameters:",
                *[
                    f"- {param.name}: {param.description}; allowed={param.allowed_values or 'free text'}"
                    for param in tool.parameters
                ],
            ]
        )

        fallback = SlotExtractionPayload(extracted_params=heuristic)
        payload = self.llm.safe_complete_json(
            system_prompt=SLOT_FILLING_SYSTEM_PROMPT,
            user_prompt=(
                f"{tool_description}\n\n"
                f"Existing parameters: {existing}\n\n"
                f"Student message:\n{text}"
            ),
            schema=SlotExtractionPayload,
            fallback=fallback,
        )

        merged = {**existing, **heuristic, **payload.extracted_params}
        return {key: value for key, value in merged.items() if value not in (None, "", [])}
