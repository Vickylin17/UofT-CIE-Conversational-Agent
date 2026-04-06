from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from schemas import SourceAttribution, ToolResult


@dataclass(slots=True)
class ToolParameter:
    name: str
    description: str
    follow_up_question: str
    allowed_values: list[str] = field(default_factory=list)


class ActionTool(ABC):
    name: str
    description: str
    parameters: list[ToolParameter]

    def required_param_names(self) -> list[str]:
        return [param.name for param in self.parameters]

    def missing_params(self, provided: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for param in self.parameters:
            value = provided.get(param.name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(param.name)
        return missing

    def follow_up_for(self, param_name: str) -> str:
        for param in self.parameters:
            if param.name == param_name:
                return param.follow_up_question
        return f"Could you share {param_name.replace('_', ' ')}?"

    @abstractmethod
    def run(self, params: dict[str, Any]) -> ToolResult:
        raise NotImplementedError

    def _build_sources(self, raw_sources: list[dict[str, str]]) -> list[SourceAttribution]:
        return [SourceAttribution(**source) for source in raw_sources]
