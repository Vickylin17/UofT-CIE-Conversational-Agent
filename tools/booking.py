from __future__ import annotations

from config import AppConfig
from schemas import ToolResult
from tools.base import KnowledgeBackedActionTool, ToolParameter


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


class AppointmentBookingTool(KnowledgeBackedActionTool):
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

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config
        if config is None:
            raise ValueError("AppointmentBookingTool requires AppConfig.")
        super().__init__(config)

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

    def run(self, params: dict[str, str], request_text: str = "", history=None) -> ToolResult:
        name = params.get("name", "").strip()
        student_status_raw = params.get("student_status", "")
        student_status = STATUS_LABELS.get(student_status_raw, student_status_raw or "student")
        contact_details = params.get("contact_details", "").strip()
        topic = params.get("topic", "").strip()
        appointment_format_raw = params.get("appointment_format", "")
        appointment_format = FORMAT_LABELS.get(appointment_format_raw, appointment_format_raw)
        folio_access = params.get("folio_access", "")
        folio_access_label = FOLIO_LABELS.get(folio_access, folio_access)

        request_summary = "\n".join(
            [
                "Here is the appointment request information I captured:",
                f"- **Name:** {name}",
                f"- **Student status:** {student_status}",
                f"- **Contact:** {contact_details}",
                f"- **Topic:** {topic}",
                f"- **Preferred format:** {appointment_format}",
                f"- **Folio access:** {folio_access_label}",
            ]
        )
        question = (
            "A student wants help with the CIE appointment booking process.\n"
            f"Name: {name}\n"
            f"Student status: {student_status}\n"
            f"Contact details: {contact_details}\n"
            f"Appointment topic: {topic}\n"
            f"Preferred format: {appointment_format}\n"
            f"Folio access: {folio_access_label}\n"
            f"Original request: {request_text or 'I want to book an appointment'}\n\n"
            "Using only the CIE knowledge base, write the most relevant next steps directly to the student.\n"
            "Answer in second person using 'you'.\n"
            "Do not narrate in third person.\n"
            "Do not say 'the assistant noted' or similar meta language.\n"
            "Do not repeat the captured fields because a summary will already be shown above.\n"
            "Explain the best booking path based on the student's Folio access and topic.\n"
            "If the knowledge base supports it, mention the relevant page or service they should use first."
        )
        result = self._grounded_answer(
            question,
            retrieval_query=f"appointment booking folio immigration advising CIE {topic}",
            history=history,
            metadata={"tool_mode": "knowledge_grounded_booking", "captured_params": params},
        )
        output = (
            f"{request_summary}\n\n"
            "I can help you prepare the request, but I cannot submit the booking for you.\n\n"
            f"{result.output}"
        )
        return ToolResult(tool_name=self.name, output=output, sources=result.sources, metadata=result.metadata)
