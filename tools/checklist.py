from __future__ import annotations

from tools.base import ActionTool, ToolParameter
from schemas import ToolResult


CHECKLISTS = {
    "undergraduate": [
        "**Admission and registration:** Review your deadlines in ACORN.",
        "**Travel documents:** Confirm your passport validity and study permit plan.",
        "**Practical setup:** Check housing, banking, and mobile options before arrival.",
        "**Health coverage:** Read UHIP and health-care onboarding information.",
    ],
    "graduate": [
        "**Graduate unit coordination:** Confirm registration and orientation timelines with your department.",
        "**Travel documents:** Prepare immigration documents and passport copies for travel and onboarding.",
        "**Funding and coverage:** Review UHIP, funding disbursement timing, and arrival logistics.",
        "**Records:** Gather academic and financial documents you may need after arrival.",
    ],
    "exchange": [
        "**Exchange deadlines:** Review course enrolment and housing timelines.",
        "**Travel documents:** Prepare immigration documents for your study period in Canada.",
        "**Insurance:** Check health insurance expectations and UHIP guidance.",
        "**Arrival plan:** Confirm key campus services for visiting students.",
    ],
    "other": [
        "**Program onboarding:** Review your registration deadlines and required setup steps.",
        "**Travel planning:** Prepare immigration, insurance, and arrival logistics.",
        "**Settlement planning:** Check housing, finances, and campus support services before you travel.",
        "**Document backup:** Keep digital and printed copies of key documents.",
    ],
}

ARRIVAL_STATUS_STEPS = {
    "not_arrived": [
        "**Travel timing:** Book travel only after your documents and timing are confirmed.",
        "**Resource review:** Set aside time to review the Pre-arrival and U of T Roadmap resources.",
    ],
    "arriving_soon": [
        "**Document folder:** Prepare printed and digital copies of your travel, immigration, and housing documents.",
        "**First-week plan:** Plan your airport-to-housing route and your first-week essentials.",
    ],
}

STATUS_LABELS = {
    "not_arrived": "planning ahead",
    "arriving_soon": "arriving soon",
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
                "Which stage best fits you right now: **planning ahead** or **arriving soon**?\n\n"
                "**Planning ahead** means you are still preparing and your trip is not imminent.\n"
                "**Arriving soon** means you expect to arrive within the next 2 to 3 weeks.\n\n"
                "If you are already in Canada, say that and I will switch to arrival-focused guidance instead."
            ),
            allowed_values=["not_arrived", "arriving_soon", "already_in_canada"],
        ),
    ]

    def run(self, params: dict[str, str]) -> ToolResult:
        student_type = params.get("student_type", "other")
        arrival_status = params.get("arrival_status", "not_arrived")
        student_label = student_type.replace("_", " ")
        article = "an" if student_label[:1].lower() in {"a", "e", "i", "o", "u"} else "a"

        if arrival_status == "already_in_canada":
            output = (
                "A **pre-arrival checklist** is meant for students who have **not reached Canada yet**.\n\n"
                "Since you are **already in Canada**, the better next step is to focus on **arrival and settlement tasks** "
                "such as **UHIP**, **SIN**, **banking**, and **campus onboarding**.\n\n"
                "If you want, I can help with those next steps or route you to the right CIE support service."
            )
            return ToolResult(tool_name=self.name, output=output, metadata={"redirected": True})

        checklist_items = CHECKLISTS.get(student_type, CHECKLISTS["other"]) + ARRIVAL_STATUS_STEPS.get(
            arrival_status, ARRIVAL_STATUS_STEPS["not_arrived"]
        )

        body = "\n".join(f"- {item}" for item in checklist_items)
        output = (
            f"Here is your **pre-arrival checklist** for **{article} {student_label} student** who is **{STATUS_LABELS.get(arrival_status, 'planning ahead')}**:\n\n"
            f"{body}"
        )
        return ToolResult(tool_name=self.name, output=output)
