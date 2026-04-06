from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PageSection(BaseModel):
    heading: str
    content: str


class RawDocument(BaseModel):
    url: str
    title: str
    category: str
    sections: list[PageSection]


class CleanDocument(BaseModel):
    url: str
    title: str
    category: str
    sections: list[PageSection]


class ChunkRecord(BaseModel):
    id: str
    text: str
    url: str
    title: str
    category: str
    section: str


class RetrievedDocument(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]
    score: float | None = None


class SourceAttribution(BaseModel):
    title: str
    url: str
    section: str


class ChatMessage(BaseModel):
    role: str
    content: str


class IntentResult(BaseModel):
    intent: str = Field(pattern="^(knowledge|action|out_of_scope)$")
    tool_name: str | None = None
    confidence: float = 0.0
    reasoning: str = ""


class ToolResult(BaseModel):
    tool_name: str
    output: str
    sources: list[SourceAttribution] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    answer: str
    intent: str
    sources: list[SourceAttribution] = Field(default_factory=list)
    follow_up_question: str | None = None
    tool_name: str | None = None
    guardrails: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    session_id: str
    history: list[ChatMessage] = Field(default_factory=list)
    active_tool: str | None = None
    collected_params: dict[str, Any] = Field(default_factory=dict)
    missing_params: list[str] = Field(default_factory=list)
    last_intent: str | None = None
    last_tool_name: str | None = None
