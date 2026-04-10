from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from config import AppConfig
from llm import LLMClient
from text_utils import match_arrival_status, match_student_type, normalize_user_text
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
        lowered = normalize_user_text(text)
        existing = existing or {}
        extracted: dict[str, Any] = {}

        if tool.name == "pre_arrival_checklist":
            student_type = match_student_type(lowered)
            arrival_status = match_arrival_status(lowered)
            if student_type:
                extracted["student_type"] = student_type
            if arrival_status:
                extracted["arrival_status"] = arrival_status

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
                cleaned_issue = re.sub(r"^(for|about|regarding)\s+", "", cleaned_issue, flags=re.I)
                cleaned_issue = re.sub(r"^(an|a|the)\s+", "", cleaned_issue, flags=re.I)
                cleaned_issue = " ".join(cleaned_issue.split()).strip(" ,.-")
                generic_values = {
                    "",
                    "advising",
                    "immigration",
                    "immigration advising",
                    "for an",
                    "for a",
                    "an",
                    "a",
                }
                generic_tokens = {"for", "an", "a", "the", "advising", "appointment", "help", "prepare"}
                issue_tokens = [token.lower() for token in re.findall(r"[A-Za-z]+", cleaned_issue)]
                has_meaningful_token = any(token not in generic_tokens for token in issue_tokens)
                if cleaned_issue.lower() not in generic_values and has_meaningful_token:
                    extracted["issue"] = cleaned_issue

        elif tool.name == "event_recommendation":
            extracted["topic"] = text.strip()

        elif tool.name == "appointment_booking":
            stripped = lowered.strip()
            email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
            if email_match:
                extracted["contact_details"] = email_match.group(0)

            if any(token in lowered for token in ["in person", "in-person"]):
                extracted["appointment_format"] = "in_person"
            elif any(token in lowered for token in ["video", "virtual", "online"]):
                extracted["appointment_format"] = "video"
            elif "phone" in lowered:
                extracted["appointment_format"] = "phone"
            elif "no preference" in lowered:
                extracted["appointment_format"] = "no_preference"

            if any(token in lowered for token in ["newly admitted", "new student", "accepted my offer", "just admitted"]):
                extracted["student_status"] = "newly_admitted"
            elif any(token in lowered for token in ["current student", "current u of t student", "studying now"]):
                extracted["student_status"] = "current_student"
            elif any(token in lowered for token in ["incoming student", "starting soon"]):
                extracted["student_status"] = "incoming_student"

            if any(token in lowered for token in ["can access folio", "i can access folio", "folio works", "yes folio"]):
                extracted["folio_access"] = "yes"
            elif any(
                token in lowered
                for token in ["cannot access folio", "can't access folio", "no folio", "dont have folio", "don't have folio"]
            ):
                extracted["folio_access"] = "no"
            elif any(token in lowered for token in ["not sure about folio", "unsure about folio", "folio not sure"]):
                extracted["folio_access"] = "not_sure"
            elif stripped in {"yes", "no", "not sure"}:
                extracted["folio_access"] = stripped.replace(" ", "_")

            topic_seed = re.sub(
                r"\b(i want to|i need to|please|book|booking|schedule|make|an|a|individual|appointment|for|with)\b",
                "",
                text,
                flags=re.I,
            )
            topic_seed = " ".join(topic_seed.split()).strip(" ,.-")
            generic_topic_values = {"", "appointment", "individual", "book"}
            if topic_seed.lower() not in generic_topic_values:
                extracted["topic"] = topic_seed

            if "name" not in existing and not extracted.get("name"):
                if not extracted.get("contact_details") and not extracted.get("student_status") and not extracted.get("appointment_format") and not extracted.get("folio_access"):
                    if (
                        1 <= len(text.strip().split()) <= 4
                        and len(topic_seed.split()) <= 4
                        and "topic" not in existing
                        and not any(token in lowered for token in ["immigration", "permit", "visa", "study", "uhip", "insurance"])
                    ):
                        extracted["name"] = text.strip()

            if "name" in existing and "contact_details" not in existing and not extracted.get("contact_details"):
                if text.strip() and not extracted.get("student_status") and not extracted.get("appointment_format") and not extracted.get("folio_access"):
                    extracted["contact_details"] = text.strip()

        return extracted

    def extract(self, tool: ActionTool, text: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        existing = existing or {}
        heuristic = self._heuristic_extract(tool, text, existing=existing)
        if not self.llm.is_available() and not self.llm.config.strict_mode:
            merged = {**existing, **heuristic}
            return {key: value for key, value in merged.items() if value not in (None, "", [])}

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
        if tool.name == "appointment_booking":
            topic = str(merged.get("topic", "")).strip().lower()
            if topic in {"yes", "no", "not sure", "in person", "in-person", "video", "phone"}:
                merged.pop("topic", None)
        return {key: value for key, value in merged.items() if value not in (None, "", [])}
