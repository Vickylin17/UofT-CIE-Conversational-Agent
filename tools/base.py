from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from config import AppConfig
from rag.service import RAGService, _replace_internal_source_refs, is_unknown_answer
from rag.prompting import format_context, format_history
from schemas import ChatMessage, SourceAttribution, ToolResult

ACTION_TOOL_SYSTEM_PROMPT = """
You are a helpful University of Toronto Centre for International Experience assistant.
Use only the supplied knowledge base context.
Answer the student's request directly and clearly.
Do not invent policies, links, dates, or services that are not supported by the context.
If the answer is not supported by the context, answer exactly: I don't know.
Never refer to supporting material as "Document 1", "Document 2", or similar internal labels.
If you refer to support, use the page title, service name, or section name instead.
""".strip()


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
    def run(
        self,
        params: dict[str, Any],
        request_text: str = "",
        history: list[ChatMessage] | None = None,
    ) -> ToolResult:
        raise NotImplementedError

    def _build_sources(self, raw_sources: list[dict[str, str]]) -> list[SourceAttribution]:
        return [SourceAttribution(**source) for source in raw_sources]


class KnowledgeBackedActionTool(ActionTool):
    def __init__(self, config: AppConfig) -> None:
        self.rag = RAGService(config)

    def _grounded_answer(
        self,
        question: str,
        retrieval_query: str | None = None,
        history: list[ChatMessage] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ToolResult:
        history = history or []
        retrieval_query = retrieval_query or question
        retrieved = self.rag.retriever.retrieve(retrieval_query)
        if not retrieved:
            return ToolResult(
                tool_name=self.name,
                output="I don't know",
                sources=[],
                metadata={"retrieval_query": retrieval_query, **(metadata or {})},
            )

        context = format_context(retrieved)
        sources = self.rag._dedupe_sources(  # noqa: SLF001
            [
                SourceAttribution(
                    title=document.metadata.get("title", "Unknown"),
                    url=document.metadata.get("url", ""),
                    section=document.metadata.get("section", "Overview"),
                )
                for document in retrieved
            ]
        )
        fallback = self.rag._extractive_fallback(question, [document.content for document in retrieved])  # noqa: SLF001
        answer = self.rag.llm.safe_complete(
            ACTION_TOOL_SYSTEM_PROMPT,
            (
                f"Conversation:\n{format_history(history)}\n\n"
                f"Student request:\n{question}\n\n"
                f"Retrieved context:\n{context}\n\n"
                "Answer the student's request using only the retrieved context."
            ),
            fallback=fallback,
        ).strip()
        if not answer:
            answer = "I don't know"

        if is_unknown_answer(answer):
            if not is_unknown_answer(fallback):
                answer = fallback.strip()
            if is_unknown_answer(answer):
                return ToolResult(
                    tool_name=self.name,
                    output="I don't know",
                    sources=[],
                    metadata={"retrieval_query": retrieval_query, **(metadata or {})},
                )

        answer = _replace_internal_source_refs(answer, sources)
        return ToolResult(
            tool_name=self.name,
            output=answer,
            sources=sources,
            metadata={"retrieval_query": retrieval_query, **(metadata or {})},
        )
