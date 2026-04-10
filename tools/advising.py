from __future__ import annotations

from uuid import uuid4

from schemas import ToolResult
from tools.base import KnowledgeBackedActionTool, ToolParameter


URGENCY_LABELS = {
    "low": "low",
    "medium": "medium",
    "high": "high",
}


class AdvisingPreparationTool(KnowledgeBackedActionTool):
    name = "advising_preparation"
    description = "Prepare a student for an advising conversation."
    parameters = [
        ToolParameter(
            name="issue",
            description="The issue the student needs advising on.",
            follow_up_question="What specific issue do you want help with at the advising appointment?",
        ),
        ToolParameter(
            name="urgency",
            description="How urgent the issue is.",
            follow_up_question="How urgent is this: low, medium, or high?",
            allowed_values=["low", "medium", "high"],
        ),
        ToolParameter(
            name="timeline",
            description="The student's current timeline or situation.",
            follow_up_question="What is your current timeline or situation? For example, upcoming travel, a deadline, or something that already happened.",
        ),
        ToolParameter(
            name="documents_ready",
            description="What supporting materials the student already has.",
            follow_up_question="What documents, emails, screenshots, or forms do you already have for this issue?",
        ),
        ToolParameter(
            name="goal",
            description="What outcome the student wants from the appointment.",
            follow_up_question="What do you want to leave the appointment with? For example, an answer, a next step, or a document checklist.",
        ),
    ]

    def missing_params(self, provided: dict[str, str]) -> list[str]:
        issue = (provided.get("issue") or "").strip().lower()
        generic_issue_phrases = {
            "prepare me for advising",
            "help me prepare for advising",
            "prepare for advising",
            "advising",
            "advising appointment",
            "immigration advising appointment",
            "for an",
            "for a",
            "an",
            "a",
        }
        if not issue or issue in generic_issue_phrases:
            return ["issue", "urgency", "timeline", "documents_ready", "goal"]

        missing: list[str] = []
        for key in ["urgency", "timeline", "documents_ready", "goal"]:
            value = (provided.get(key) or "").strip()
            if not value:
                missing.append(key)
        return missing

    def run(self, params: dict[str, str], request_text: str = "", history=None):
        issue = params.get("issue", "general support").strip()
        urgency = params.get("urgency", "medium").strip()
        timeline = params.get("timeline", "").strip()
        documents_ready = params.get("documents_ready", "").strip()
        goal = params.get("goal", "").strip()
        is_immigration = any(token in issue.lower() for token in ["immigration", "permit", "visa", "trv", "pgwp"])

        question = (
            "A student wants help preparing for a CIE advising appointment.\n"
            f"Main issue: {issue}\n"
            f"Urgency: {urgency}\n"
            f"Timeline: {timeline}\n"
            f"Documents already available: {documents_ready}\n"
            f"Desired outcome: {goal}\n"
            f"Original request: {request_text or 'Help me prepare for advising'}\n\n"
            "Using only the CIE knowledge base, provide a tailored appointment preparation summary. "
            "Include what the student should bring, what to clarify before the appointment, and the most relevant next steps."
        )
        return self._grounded_answer(
            question,
            retrieval_query=f"{issue} advising appointment CIE immigration support documents next steps",
            history=history,
            metadata={
                "needs_disclaimer": is_immigration,
                "tool_mode": "knowledge_grounded_advising",
            },
        )
