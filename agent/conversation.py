from __future__ import annotations

from uuid import uuid4

from agent.intent import IntentClassifier
from agent.slot_filling import SlotFiller
from config import AppConfig
from guardrails.policies import (
    detect_prompt_injection,
    immigration_disclaimer,
    is_capability_question,
    is_greeting,
    is_out_of_scope_query,
    needs_immigration_disclaimer,
    sanitize_user_input,
)
from memory.store import JSONMemoryStore
from rag.service import RAGService
from schemas import AgentResponse, ChatMessage, SessionState
from tools.registry import ToolRegistry


class ConversationAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.memory = JSONMemoryStore(config.paths.session_store_path)
        self.intent_classifier = IntentClassifier(config)
        self.slot_filler = SlotFiller(config)
        self.tool_registry = ToolRegistry(config)
        self.rag = RAGService(config)

    def new_session_id(self) -> str:
        return str(uuid4())

    def _load_session(self, session_id: str) -> SessionState:
        return self.memory.get_session(session_id)

    def _save_session(self, session: SessionState) -> None:
        self.memory.save_session(session)

    def _append_immigration_disclaimer(self, text: str, guardrails: list[str]) -> str:
        disclaimer = immigration_disclaimer()
        lowered = text.lower()
        if disclaimer.lower() in lowered or "not legal advice" in lowered:
            return text
        guardrails.append("immigration_disclaimer")
        return f"{text}\n\n{disclaimer}"

    def _capabilities_response(self) -> str:
        return (
            "You can ask me about the UofT CIE Resource Hub, including pre-arrival planning, upon-arrival steps, "
            "UHIP, finances, immigration information in the hub, peer support, and relevant events. "
            "I can also generate a pre-arrival checklist, route you to the right CIE support service, "
            "prepare you for an advising appointment, and recommend relevant sessions."
        )

    def _greeting_response(self) -> str:
        return (
            "Hello! I can help with UofT CIE Resource Hub questions, pre-arrival checklists, support routing, "
            "advising preparation, and event recommendations. Ask me something like "
            "`What does the hub say about UHIP?` or `Give me a pre-arrival checklist.`"
        )

    def _finalize_response(self, session: SessionState, answer: str, response: AgentResponse) -> AgentResponse:
        session.history.append(ChatMessage(role="assistant", content=answer))
        self._save_session(session)
        return response

    def _handle_tool_turn(self, session: SessionState, message: str) -> AgentResponse:
        tool = self.tool_registry.get(session.active_tool or "")
        if tool is None:
            session.active_tool = None
            session.collected_params = {}
            session.missing_params = []
            self._save_session(session)
            return AgentResponse(answer="I don't know", intent="action")

        params = self.slot_filler.extract(tool, message, existing=session.collected_params)
        session.collected_params = params
        missing = tool.missing_params(params)
        session.missing_params = missing

        if missing:
            follow_up = tool.follow_up_for(missing[0])
            self._save_session(session)
            return AgentResponse(
                answer=follow_up,
                intent="action",
                follow_up_question=follow_up,
                tool_name=tool.name,
                metadata={"missing_params": missing},
            )

        result = tool.run(params)
        guardrails: list[str] = []
        answer = result.output
        if result.metadata.get("needs_disclaimer", False):
            answer = self._append_immigration_disclaimer(answer, guardrails)

        session.active_tool = None
        session.collected_params = {}
        session.missing_params = []
        session.last_tool_name = tool.name
        self._save_session(session)
        return AgentResponse(
            answer=answer,
            intent="action",
            tool_name=tool.name,
            sources=result.sources,
            guardrails=guardrails,
            metadata=result.metadata,
        )

    def handle_message(self, message: str, session_id: str | None = None) -> tuple[str, AgentResponse]:
        session_id = session_id or self.new_session_id()
        session = self._load_session(session_id)
        guardrails: list[str] = []

        sanitized_message = sanitize_user_input(message)
        if detect_prompt_injection(message):
            guardrails.append("prompt_injection_detected")
        if is_greeting(sanitized_message):
            answer = self._greeting_response()
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(answer=answer, intent="knowledge", guardrails=guardrails)
            return session_id, self._finalize_response(session, answer, response)
        if is_capability_question(sanitized_message):
            answer = self._capabilities_response()
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(answer=answer, intent="knowledge", guardrails=guardrails)
            return session_id, self._finalize_response(session, answer, response)
        if is_out_of_scope_query(sanitized_message):
            answer = "I can only help with University of Toronto CIE and international student support topics."
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(answer=answer, intent="out_of_scope", guardrails=guardrails)
            return session_id, self._finalize_response(session, answer, response)

        session.history.append(ChatMessage(role="user", content=message))

        if session.active_tool:
            response = self._handle_tool_turn(session, sanitized_message)
            response.guardrails.extend(guardrails)
            return session_id, self._finalize_response(session, response.answer, response)

        intent = self.intent_classifier.classify(sanitized_message)
        session.last_intent = intent.intent

        if intent.intent == "out_of_scope":
            answer = "I can only help with University of Toronto CIE and international student support topics."
            response = AgentResponse(answer=answer, intent="out_of_scope", guardrails=guardrails)
            return session_id, self._finalize_response(session, answer, response)

        if intent.intent == "action":
            tool = self.tool_registry.get(intent.tool_name or "")
            if tool is None:
                answer = "I don't know"
                response = AgentResponse(answer=answer, intent="action", guardrails=guardrails)
                return session_id, self._finalize_response(session, answer, response)

            params = self.slot_filler.extract(tool, sanitized_message)
            missing = tool.missing_params(params)
            session.active_tool = tool.name
            session.collected_params = params
            session.missing_params = missing

            if missing:
                follow_up = tool.follow_up_for(missing[0])
                self._save_session(session)
                response = AgentResponse(
                    answer=follow_up,
                    intent="action",
                    follow_up_question=follow_up,
                    tool_name=tool.name,
                    guardrails=guardrails,
                    metadata={"missing_params": missing},
                )
                return session_id, self._finalize_response(session, follow_up, response)

            response = self._handle_tool_turn(session, sanitized_message)
            response.guardrails.extend(guardrails)
            return session_id, self._finalize_response(session, response.answer, response)

        answer, sources, retrieval_query = self.rag.answer(sanitized_message, history=session.history[:-1])
        if needs_immigration_disclaimer(message) or needs_immigration_disclaimer(answer):
            answer = self._append_immigration_disclaimer(answer, guardrails)

        response = AgentResponse(
            answer=answer,
            intent="knowledge",
            sources=sources,
            guardrails=guardrails,
            metadata={"retrieval_query": retrieval_query},
        )
        return session_id, self._finalize_response(session, answer, response)
