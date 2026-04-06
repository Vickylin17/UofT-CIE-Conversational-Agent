from __future__ import annotations

from config import AppConfig
from tools.advising import AdvisingPreparationTool
from tools.base import ActionTool
from tools.checklist import PreArrivalChecklistTool
from tools.events import EventRecommendationTool
from tools.routing import SupportRoutingTool


class ToolRegistry:
    def __init__(self, config: AppConfig) -> None:
        tools: list[ActionTool] = [
            PreArrivalChecklistTool(),
            SupportRoutingTool(),
            AdvisingPreparationTool(),
            EventRecommendationTool(config),
        ]
        self.tools = {tool.name: tool for tool in tools}

    def get(self, tool_name: str) -> ActionTool | None:
        return self.tools.get(tool_name)

    def names(self) -> list[str]:
        return list(self.tools.keys())
