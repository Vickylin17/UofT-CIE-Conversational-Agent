from __future__ import annotations

from tools.base import ActionTool, ToolParameter
from schemas import ToolResult


URGENCY_GUIDANCE = {
    "low": "Plan ahead and gather documents before reaching out.",
    "medium": "Prepare your documents and timeline, then contact support promptly.",
    "high": "Prioritize contacting the relevant CIE service as soon as possible and keep your documents ready.",
}


class AdvisingPreparationTool(ActionTool):
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
        }
        if not issue or issue in generic_issue_phrases:
            return ["issue", "urgency", "timeline", "documents_ready", "goal"]

        missing: list[str] = []
        for key in ["urgency", "timeline", "documents_ready", "goal"]:
            value = (provided.get(key) or "").strip()
            if not value:
                missing.append(key)
        return missing

    def run(self, params: dict[str, str]) -> ToolResult:
        issue = params.get("issue", "general support")
        urgency = params.get("urgency", "medium")
        timeline = params.get("timeline", "")
        documents_ready = params.get("documents_ready", "")
        goal = params.get("goal", "")
        urgency_note = URGENCY_GUIDANCE.get(urgency, URGENCY_GUIDANCE["medium"])
        is_immigration = "immigration" in issue.lower() or "permit" in issue.lower() or "visa" in issue.lower()

        output = (
            "Here is your advising preparation summary.\n\n"
            f"Main issue: {issue}\n"
            f"Urgency: {urgency}\n"
            f"Current timeline: {timeline}\n"
            f"Documents you already have: {documents_ready}\n"
            f"What you want from the appointment: {goal}\n\n"
            "What to bring or prepare:\n"
            "- Your U of T student number\n"
            "- A short timeline of what happened and when\n"
            "- Relevant emails, forms, screenshots, and supporting documents\n"
            "- A short list of questions you want answered\n\n"
            f"Preparation note: {urgency_note}"
        )
        return ToolResult(tool_name=self.name, output=output, metadata={"needs_disclaimer": is_immigration})
