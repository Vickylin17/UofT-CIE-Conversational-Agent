from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    case_id: str
    category: str
    turns: list[str]
    expected_intent: str
    expected_tool: str | None = None
    expected_keywords: list[str] = Field(default_factory=list)
    forbidden_keywords: list[str] = Field(default_factory=list)
    expect_follow_up: bool = False
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    case_id: str
    category: str
    passed: bool
    scores: dict[str, float]
    expected_intent: str
    predicted_intent: str
    expected_tool: str | None = None
    predicted_tool: str | None = None
    answer: str
    notes: str = ""
