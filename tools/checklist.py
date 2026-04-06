from __future__ import annotations

from tools.base import ActionTool, ToolParameter
from schemas import ToolResult


CHECKLISTS = {
    "undergraduate": [
        "Review your admission and registration deadlines in ACORN.",
        "Confirm your travel documents, passport validity, and study permit plan.",
        "Check housing, banking, and mobile setup before arrival.",
        "Read UHIP and health-care onboarding information.",
    ],
    "graduate": [
        "Coordinate with your graduate unit on registration and orientation timelines.",
        "Prepare immigration documents and passport copies for travel and onboarding.",
        "Review UHIP, funding disbursement timing, and arrival logistics.",
        "Gather academic and financial records you may need after arrival.",
    ],
    "exchange": [
        "Review exchange-specific deadlines, course enrolment, and housing timelines.",
        "Prepare travel and immigration documents for your study period in Canada.",
        "Check health insurance expectations and UHIP guidance.",
        "Confirm arrival plans and key campus services for visiting students.",
    ],
    "other": [
        "Review your program onboarding tasks and registration deadlines.",
        "Prepare travel, immigration, insurance, and arrival logistics.",
        "Check housing, finances, and campus support services before you travel.",
        "Keep digital and printed copies of key documents.",
    ],
}

ARRIVAL_STATUS_STEPS = {
    "not_arrived": [
        "Book travel only after your documents and timing are confirmed.",
        "Set aside time to review the Pre-arrival and U of T Roadmap resources.",
    ],
    "arriving_soon": [
        "Prepare printed and digital copies of your travel, immigration, and housing documents.",
        "Plan your airport-to-housing route and your first-week essentials.",
    ],
    "already_in_canada": [
        "Shift your focus to upon-arrival tasks like UHIP setup, SIN, banking, and campus onboarding.",
        "Use the hub's support services if any immigration or settlement issue remains unresolved.",
    ],
}


class PreArrivalChecklistTool(ActionTool):
    name = "pre_arrival_checklist"
    description = "Generate a personalized pre-arrival checklist."
    parameters = [
        ToolParameter(
            name="student_type",
            description="The student's academic profile.",
            follow_up_question=(
                "Which student type best fits you: undergraduate, graduate, exchange, or other?"
            ),
            allowed_values=["undergraduate", "graduate", "exchange", "other"],
        ),
        ToolParameter(
            name="arrival_status",
            description="The student's current arrival stage.",
            follow_up_question=(
                "What is your arrival status: not_arrived, arriving_soon, or already_in_canada?"
            ),
            allowed_values=["not_arrived", "arriving_soon", "already_in_canada"],
        ),
    ]

    def run(self, params: dict[str, str]) -> ToolResult:
        student_type = params.get("student_type", "other")
        arrival_status = params.get("arrival_status", "not_arrived")
        checklist_items = CHECKLISTS.get(student_type, CHECKLISTS["other"]) + ARRIVAL_STATUS_STEPS.get(
            arrival_status, ARRIVAL_STATUS_STEPS["not_arrived"]
        )

        body = "\n".join(f"- {item}" for item in checklist_items)
        output = (
            f"Personalized pre-arrival checklist for a {student_type.replace('_', ' ')} student "
            f"with status `{arrival_status}`:\n{body}"
        )
        return ToolResult(tool_name=self.name, output=output)
