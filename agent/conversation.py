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
from text_utils import normalize_user_text
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

    def _update_session_title(self, session: SessionState, message: str) -> None:
        normalized = " ".join(message.split()).strip()
        if not normalized:
            return
        if session.title and session.title != "New chat":
            return
        lowered = normalized.lower()
        if lowered in {"hi", "hello", "hey", "what can i ask you", "what can you do"}:
            return
        session.title = normalized[:48]

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
            "prepare you for an advising appointment, help you collect booking details for an individual appointment, "
            "and recommend relevant sessions."
        )

    def _greeting_response(self) -> str:
        return (
            "Hello! I can help with UofT CIE Resource Hub questions, pre-arrival checklists, support routing, "
            "advising preparation, appointment booking intake, and event recommendations. Ask me something like "
            "`What does the hub say about UHIP?` or `Give me a pre-arrival checklist.`"
        )

    def _looks_like_new_request(self, message: str) -> bool:
        lowered = " ".join(message.lower().split()).strip()
        if not lowered:
            return False
        return any(
            lowered.startswith(prefix)
            for prefix in [
                "where can i find",
                "where do i find",
                "what does",
                "what is",
                "who should i contact",
                "who do i contact",
                "can you help",
                "can i",
                "give me",
                "show me",
                "recommend",
                "route me",
                "help me",
                "i need",
                "tell me about",
                "find information",
                "information about",
                "how do i",
                "how can i",
            ]
        )

    def _message_matches_active_tool(self, session: SessionState, message: str) -> bool:
        tool_name = session.active_tool or ""
        missing = session.missing_params[0] if session.missing_params else ""
        lowered = " ".join(message.lower().split()).strip()

        if not tool_name or not missing:
            return False

        if tool_name == "advising_preparation":
            if missing == "urgency":
                return lowered in {"low", "medium", "high"} or any(
                    token in lowered
                    for token in ["urgent", "asap", "immediately", "not urgent", "later", "this week", "soon"]
                )
            if missing in {"issue", "timeline", "documents_ready", "goal"}:
                return not self._looks_like_new_request(message)

        if tool_name == "pre_arrival_checklist":
            if missing == "student_type":
                return any(token in lowered for token in ["undergrad", "undergraduate", "graduate", "masters", "phd", "exchange", "visiting", "other"])
            if missing == "arrival_status":
                return any(
                    token in lowered
                    for token in [
                        "planning ahead",
                        "arriving soon",
                        "already in canada",
                        "i'm in canada",
                        "i am in canada",
                        "next week",
                        "not arrived",
                    ]
                )

        if tool_name in {"support_routing", "event_recommendation"}:
            return True

        if tool_name == "appointment_booking":
            return True

        return not self._looks_like_new_request(message)

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
        normalized_message = normalize_user_text(sanitized_message)
        if detect_prompt_injection(message):
            guardrails.append("prompt_injection_detected")
        if is_greeting(normalized_message):
            answer = self._greeting_response()
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(answer=answer, intent="knowledge", guardrails=guardrails)
            return session_id, self._finalize_response(session, answer, response)
        if is_capability_question(normalized_message):
            answer = self._capabilities_response()
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(answer=answer, intent="knowledge", guardrails=guardrails)
            return session_id, self._finalize_response(session, answer, response)
        if is_out_of_scope_query(normalized_message):
            answer = "I can only help with University of Toronto CIE and international student support topics."
            self._update_session_title(session, message)
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(answer=answer, intent="out_of_scope", guardrails=guardrails)
            return session_id, self._finalize_response(session, answer, response)

        self._update_session_title(session, message)
        session.history.append(ChatMessage(role="user", content=message))

        if session.active_tool:
            if self._message_matches_active_tool(session, normalized_message):
                response = self._handle_tool_turn(session, sanitized_message)
                response.guardrails.extend(guardrails)
                return session_id, self._finalize_response(session, response.answer, response)

            session.active_tool = None
            session.collected_params = {}
            session.missing_params = []
            self._save_session(session)

        intent = self.intent_classifier.classify(normalized_message)
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

        answer, sources, retrieval_query = self.rag.answer(normalized_message, history=session.history[:-1])
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
