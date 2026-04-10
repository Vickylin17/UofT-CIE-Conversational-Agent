from __future__ import annotations

from config import AppConfig
from tools.base import KnowledgeBackedActionTool, ToolParameter


class EventRecommendationTool(KnowledgeBackedActionTool):
    name = "event_recommendation"
    description = "Recommend relevant hub sessions or events."
    parameters = [
        ToolParameter(
            name="topic",
            description="The student's topic of interest.",
            follow_up_question="What topic are you interested in for events or sessions?",
        )
    ]

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config)

    def run(self, params: dict[str, str], request_text: str = "", history=None):
        topic = params.get("topic", "").strip() or request_text.strip()
        question = (
            "A student wants recommendations for CIE events or sessions.\n"
            f"Topic of interest: {topic}\n"
            f"Original request: {request_text or topic}\n\n"
            "Using only the CIE knowledge base, recommend the most relevant events, workshops, or sessions. "
            "Include names and dates only if they appear in the knowledge base context."
        )
        return self._grounded_answer(
            question,
            retrieval_query=f"{topic} programs events workshops sessions CIE",
            history=history,
            metadata={"tool_mode": "knowledge_grounded_events"},
        )
