from __future__ import annotations

from tools.base import ActionTool, ToolParameter
from schemas import SourceAttribution, ToolResult


FORMAT_LABELS = {
    "in_person": "in-person",
    "video": "video",
    "phone": "phone",
    "no_preference": "no preference",
}

STATUS_LABELS = {
    "newly_admitted": "newly admitted student",
    "incoming_student": "incoming student",
    "current_student": "current student",
}

FOLIO_LABELS = {
    "yes": "Yes",
    "no": "No",
    "not_sure": "Not sure",
}


class AppointmentBookingTool(ActionTool):
    name = "appointment_booking"
    description = "Collect appointment booking details and guide the student to the right CIE booking path."
    parameters = [
        ToolParameter(
            name="name",
            description="The student's name.",
            follow_up_question="What name should I put on your appointment request summary?",
        ),
        ToolParameter(
            name="student_status",
            description="Whether the student is newly admitted, incoming, or current.",
            follow_up_question="Are you newly admitted, incoming, or a current U of T student?",
            allowed_values=["newly_admitted", "incoming_student", "current_student"],
        ),
        ToolParameter(
            name="contact_details",
            description="The best contact detail to include in the request.",
            follow_up_question="What is the best contact detail to include, such as your U of T email?",
        ),
        ToolParameter(
            name="topic",
            description="What the appointment is about.",
            follow_up_question="What do you want the appointment to be about?",
        ),
        ToolParameter(
            name="appointment_format",
            description="Preferred appointment format.",
            follow_up_question="Do you prefer an in-person, phone, video appointment, or no preference?",
            allowed_values=["in_person", "phone", "video", "no_preference"],
        ),
        ToolParameter(
            name="folio_access",
            description="Whether the student can access Folio.",
            follow_up_question="Can you access Folio right now: yes, no, or not sure?",
            allowed_values=["yes", "no", "not_sure"],
        ),
    ]

    def missing_params(self, provided: dict[str, str]) -> list[str]:
        missing: list[str] = []
        invalid_topic_values = {"", "yes", "no", "not sure", "in person", "in-person", "video", "phone"}

        for param in self.parameters:
            value = (provided.get(param.name) or "").strip()
            if param.name == "topic":
                if value.lower() in invalid_topic_values:
                    missing.append(param.name)
                continue
            if not value:
                missing.append(param.name)
        return missing

    def run(self, params: dict[str, str]) -> ToolResult:
        name = params.get("name", "").strip()
        student_status = STATUS_LABELS.get(params.get("student_status", ""), params.get("student_status", "student"))
        contact_details = params.get("contact_details", "").strip()
        topic = params.get("topic", "").strip()
        appointment_format = FORMAT_LABELS.get(params.get("appointment_format", ""), params.get("appointment_format", ""))
        folio_access = params.get("folio_access", "")

        request_summary = "\n".join(
            [
                "Here is the appointment request information I captured:",
                f"- Name: {name}",
                f"- Student status: {student_status}",
                f"- Contact: {contact_details}",
                f"- Topic: {topic}",
                f"- Preferred format: {appointment_format}",
                f"- Folio access: {FOLIO_LABELS.get(folio_access, folio_access)}",
            ]
        )

        if folio_access == "yes":
            next_step = (
                "Next step: open Folio, go to the Appointments section, choose `Immigration Advising - CIE`, "
                "pick your preferred time, and complete the intake form in the confirmation email."
            )
        elif folio_access == "no":
            next_step = (
                "Next step: if you are newly admitted, accept your U of T offer first so Folio becomes available. "
                "If you are already a student and still cannot access Folio, email `isa.cie@utoronto.ca` with the summary above "
                "and ask for help booking or temporary re-activation."
            )
        else:
            next_step = (
                "Next step: try signing into Folio first. If it does not work, email `isa.cie@utoronto.ca` with the summary above "
                "and ask whether they can help you access booking."
            )

        output = (
            f"{request_summary}\n\n"
            "I can help you prepare the request, but I cannot submit the booking for you.\n\n"
            f"{next_step}"
        )
        sources = [
            SourceAttribution(
                title="Connecting with ISIAs",
                url="https://internationalexperience.utoronto.ca/international-student-services/immigration/connecting-with-isias",
                section="Appointments",
            )
        ]
        return ToolResult(tool_name=self.name, output=output, sources=sources)
