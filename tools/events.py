from __future__ import annotations

from config import AppConfig
from rag.retriever import Retriever
from schemas import SourceAttribution, ToolResult
from tools.base import ActionTool, ToolParameter


class EventRecommendationTool(ActionTool):
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
        self.retriever = Retriever(config)

    def run(self, params: dict[str, str]) -> ToolResult:
        topic = params.get("topic", "")
        docs = self.retriever.retrieve(f"event session workshop {topic}", top_k=3)
        if not docs:
            return ToolResult(tool_name=self.name, output="I don't know")

        lines = []
        sources: list[SourceAttribution] = []
        for doc in docs:
            title = doc.metadata.get("title", "Unknown")
            section = doc.metadata.get("section", "Overview")
            lines.append(f"- {title} ({section})")
            sources.append(
                SourceAttribution(title=title, url=doc.metadata.get("url", ""), section=section)
            )

        output = "Relevant sessions or events I found:\n" + "\n".join(lines)
        return ToolResult(tool_name=self.name, output=output, sources=sources)
