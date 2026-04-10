from __future__ import annotations

import re
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
from llm import LLMClient
from memory.store import JSONMemoryStore
from rag.service import RAGService
from schemas import AgentResponse, ChatMessage, SessionState
from text_utils import match_arrival_status, match_student_type, normalize_user_text
from tools.registry import ToolRegistry


ACTION_FOLLOW_UP_SYSTEM_PROMPT = """
You are a University of Toronto CIE support chatbot collecting parameters for an action.
Ask exactly one concise follow-up question for the next missing field.
Use the tool and collected parameters for context.
Do not ask for more than one missing field at a time.
Do not invent requirements beyond the tool schema.
Do not say meta phrases such as "the assistant noted" or "I have recorded that".
Do not restate previously captured information unless it helps clarify the next question.
End with the exact next question you want the student to answer.
""".strip()


SESSION_MEMORY_SYSTEM_PROMPT = """
You answer questions about the current conversation session only.
Use only the provided transcript and cited sources from earlier turns in this session.
If the requested detail was not mentioned earlier in the session, answer exactly:
I don't have that earlier in this session.
Do not invent details and do not use outside knowledge.
Keep the answer concise and directly answer the memory question.
""".strip()

MEMORY_QUERY_PATTERNS = [
    r"\bwhat did (?:you|i) (?:say|mention|ask)\b",
    r"\bwhat was (?:my|your) (?:last|previous) (?:question|answer|reply)\b",
    r"\bwhat did we talk about\b",
    r"\bwhat have we talked about\b",
    r"\bcan you remind me\b",
    r"\bremind me what\b",
    r"\byou mentioned earlier\b",
    r"\byou said earlier\b",
    r"\bearlier in (?:this|the) session\b",
    r"\bfrom earlier\b",
    r"\bpreviously\b",
    r"\brecap (?:this|our) (?:chat|session|conversation)\b",
]

ACTIVE_TOOL_STATUS_PATTERNS = [
    r"\bwhat do you have so far\b",
    r"\bwhat information do you have\b",
    r"\bwhat have you collected\b",
    r"\bwhat do you still need\b",
    r"\bwhat are you missing\b",
    r"\bcan you summarize\b",
    r"\bsummary so far\b",
    r"\bshow me what you have\b",
]

MEMORY_STOPWORDS = {
    "about",
    "answer",
    "asked",
    "before",
    "chat",
    "conversation",
    "did",
    "earlier",
    "from",
    "have",
    "i",
    "in",
    "it",
    "last",
    "me",
    "mention",
    "mentioned",
    "my",
    "of",
    "our",
    "previous",
    "previously",
    "question",
    "recap",
    "remind",
    "reply",
    "said",
    "say",
    "session",
    "that",
    "the",
    "this",
    "to",
    "talk",
    "talked",
    "we",
    "what",
    "you",
    "your",
}

MEMORY_FACT_TERMS = {
    "reference",
    "number",
    "ref",
    "email",
    "contact",
    "status",
    "topic",
    "format",
    "folio",
    "name",
}

BOOKING_FIELD_LABELS = {
    "reference_number": "Reference number",
    "name": "Name",
    "student_status": "Student status",
    "contact_details": "Contact",
    "topic": "Topic",
    "appointment_format": "Preferred format",
    "folio_access": "Folio access",
}

ADVISING_FIELD_LABELS = {
    "reference_number": "Reference number",
    "issue": "Main issue",
    "urgency": "Urgency",
    "timeline": "Current timeline",
    "documents_ready": "Documents you already have",
    "goal": "What you want from the appointment",
}

BOOKING_VALUE_LABELS = {
    "student_status": {
        "newly_admitted": "newly admitted student",
        "incoming_student": "incoming student",
        "current_student": "current student",
    },
    "appointment_format": {
        "in_person": "in-person",
        "phone": "phone",
        "video": "video",
        "no_preference": "no preference",
    },
    "folio_access": {
        "yes": "Yes",
        "no": "No",
        "not_sure": "Not sure",
    },
}


class ConversationAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = LLMClient(config.llm)
        if self.config.llm.strict_mode:
            self.llm.require_available("the conversational agent")
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
                return match_student_type(lowered) is not None
            if missing == "arrival_status":
                return match_arrival_status(lowered) is not None

        if tool_name in {"support_routing", "event_recommendation"}:
            return True

        if tool_name == "appointment_booking":
            return True

        return not self._looks_like_new_request(message)

    def _finalize_response(self, session: SessionState, answer: str, response: AgentResponse) -> AgentResponse:
        session.history.append(ChatMessage(role="assistant", content=answer, sources=response.sources))
        self._save_session(session)
        return response

    def _session_memory_history(self, session: SessionState) -> list[ChatMessage]:
        if session.history and session.history[-1].role == "user":
            return session.history[:-1]
        return session.history

    def _is_memory_recall_query(self, message: str) -> bool:
        lowered = normalize_user_text(message)
        if any(re.search(pattern, lowered) for pattern in MEMORY_QUERY_PATTERNS):
            return True

        memory_markers = {"earlier", "previous", "previously", "last", "before", "remind", "mentioned", "said"}
        recall_targets = {"question", "answer", "reply", "email", "contact", "link", "source", "page", "website"}
        if any(marker in lowered for marker in memory_markers) and any(target in lowered for target in recall_targets):
            return True
        return any(term in lowered for term in MEMORY_FACT_TERMS)

    def _history_tokens(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9@._/-]+", normalize_user_text(text))
            if len(token) > 2 and token not in MEMORY_STOPWORDS
        }

    def _source_labels(self, message: ChatMessage) -> str:
        parts: list[str] = []
        for source in message.sources:
            if source.title:
                parts.append(source.title)
            if source.section and source.section not in parts:
                parts.append(source.section)
        return " ".join(parts)

    def _best_matching_message(self, history: list[ChatMessage], query: str, role: str | None = None) -> ChatMessage | None:
        query_tokens = self._history_tokens(query)
        candidates = [message for message in history if role is None or message.role == role]
        best_message: ChatMessage | None = None
        best_score = -1

        for index, message in enumerate(candidates):
            searchable = f"{message.content} {self._source_labels(message)}"
            message_tokens = self._history_tokens(searchable)
            overlap = len(query_tokens & message_tokens)
            score = overlap * 10 + index
            if ("email" in query_tokens or "contact" in query_tokens) and re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", searchable):
                score += 6
            if any(token in query_tokens for token in {"link", "url", "website", "source", "page"}) and message.sources:
                score += 4
            if score > best_score:
                best_score = score
                best_message = message

        return best_message

    def _extract_relevant_excerpt(self, message: ChatMessage, query: str) -> str:
        query_tokens = self._history_tokens(query)
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", message.content) if sentence.strip()]
        if not sentences:
            return message.content.strip()

        best_sentence = sentences[0]
        best_score = -1
        for index, sentence in enumerate(sentences):
            sentence_tokens = self._history_tokens(sentence)
            overlap = len(query_tokens & sentence_tokens)
            score = overlap * 10 - index
            if ("email" in query_tokens or "contact" in query_tokens) and re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", sentence):
                score += 6
            if any(token in query_tokens for token in {"link", "url", "website"}) and ("http" in sentence or "www." in sentence):
                score += 6
            if score > best_score:
                best_score = score
                best_sentence = sentence
        return best_sentence

    def _memory_recall_fallback(self, session: SessionState, message: str) -> str:
        history = self._session_memory_history(session)
        if not history:
            return "I don't have anything earlier in this session yet."

        lowered = normalize_user_text(message)
        previous_user_messages = [item for item in history if item.role == "user" and item.content.strip()]
        previous_assistant_messages = [item for item in history if item.role == "assistant" and item.content.strip()]

        if any(phrase in lowered for phrase in ["my last question", "my previous question", "what did i ask"]):
            if not previous_user_messages:
                return "I don't have an earlier user question in this session yet."
            return f'Your previous question in this session was: "{previous_user_messages[-1].content.strip()}"'

        if any(phrase in lowered for phrase in ["your last answer", "your previous answer", "what did you say", "what did you mention"]):
            if not previous_assistant_messages:
                return "I don't have an earlier answer in this session yet."

        if any(phrase in lowered for phrase in ["what did we talk about", "what have we talked about", "recap this chat", "recap our conversation"]):
            recent_questions = [item.content.strip() for item in previous_user_messages[-3:] if item.content.strip()]
            if not recent_questions:
                return "I don't have enough earlier conversation in this session to recap yet."
            bullets = "\n".join(f"- {question}" for question in recent_questions)
            return f"Earlier in this session, you asked about:\n{bullets}"

        target_role = "assistant"
        if any(phrase in lowered for phrase in ["my last question", "my previous question", "what did i ask"]):
            target_role = "user"

        matched = self._best_matching_message(history, message, role=target_role)
        if matched is None:
            return "I don't have that earlier in this session."

        if any(token in lowered for token in ["email", "contact"]):
            emails = re.findall(r"[\w.\-+]+@[\w.\-]+\.\w+", matched.content)
            if emails:
                return f"Earlier in this session, I mentioned this email: `{emails[0]}`"

        if any(token in lowered for token in ["link", "website", "url", "page", "source"]):
            if matched.sources:
                labels = []
                for source in matched.sources[:3]:
                    if source.section and source.section != source.title:
                        labels.append(f"{source.title} ({source.section})")
                    else:
                        labels.append(source.title)
                return "Earlier in this session, I cited: " + ", ".join(labels)

        excerpt = self._extract_relevant_excerpt(matched, message)
        prefix = "Earlier in this session, you asked:" if matched.role == "user" else "Earlier in this session, I said:"
        return f"{prefix} {excerpt}"

    def _memory_recall_response(self, session: SessionState, message: str) -> str | None:
        if not self._is_memory_recall_query(message):
            return None

        history = self._session_memory_history(session)
        if not history:
            return "I don't have anything earlier in this session yet."

        lowered = normalize_user_text(message)
        if any(term in lowered for term in MEMORY_FACT_TERMS):
            has_email = any(re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", item.content) for item in history)
            combined_tokens = set().union(*(self._history_tokens(item.content) for item in history if item.content.strip()))
            query_tokens = self._history_tokens(message)
            informative_tokens = query_tokens - MEMORY_FACT_TERMS
            if not has_email and "email" in lowered and not informative_tokens:
                return None
            if informative_tokens and not (informative_tokens & combined_tokens):
                if not ("email" in lowered and has_email):
                    return None

        fallback = self._memory_recall_fallback(session, message)
        if not self.llm.is_available():
            return fallback

        transcript_lines: list[str] = []
        for item in history[-12:]:
            line = f"{item.role.title()}: {item.content}"
            if item.sources:
                labels = ", ".join(source.title for source in item.sources[:3] if source.title)
                if labels:
                    line += f" | Sources: {labels}"
            transcript_lines.append(line)

        answer = self.llm.safe_complete(
            SESSION_MEMORY_SYSTEM_PROMPT,
            (
                f"Conversation transcript:\n{chr(10).join(transcript_lines)}\n\n"
                f"Student memory question:\n{message}"
            ),
            fallback=fallback,
        ).strip()
        return answer or fallback

    def _is_active_tool_status_query(self, message: str) -> bool:
        lowered = normalize_user_text(message)
        return any(re.search(pattern, lowered) for pattern in ACTIVE_TOOL_STATUS_PATTERNS)

    def _format_collected_value(self, tool_name: str, field_name: str, value: str) -> str:
        if tool_name == "appointment_booking":
            return BOOKING_VALUE_LABELS.get(field_name, {}).get(value, value.replace("_", " "))
        return value.replace("_", " ")

    def _render_active_tool_status(self, session: SessionState) -> str:
        tool = self.tool_registry.get(session.active_tool or "")
        if tool is None:
            return "I don't have an active action in progress right now."

        if not session.collected_params and not session.missing_params:
            return "I don't have any details collected for the current action yet."

        lines = [f"Here is what I have so far for **{tool.name.replace('_', ' ')}**:"]
        if session.collected_params:
            for param in tool.parameters:
                value = str(session.collected_params.get(param.name, "")).strip()
                if not value:
                    continue
                label = BOOKING_FIELD_LABELS.get(param.name, param.name.replace("_", " ").title())
                formatted_value = self._format_collected_value(tool.name, param.name, value)
                lines.append(f"- **{label}:** {formatted_value}")
        else:
            lines.append("- No details collected yet.")

        if session.missing_params:
            next_label = BOOKING_FIELD_LABELS.get(session.missing_params[0], session.missing_params[0].replace("_", " ").title())
            lines.append("")
            lines.append(f"I still need **{next_label.lower()}** next.")
            lines.append(tool.follow_up_for(session.missing_params[0]))
        else:
            lines.append("")
            lines.append("I already have everything I need for this action.")
        return "\n".join(lines)

    def _render_follow_up(self, tool_name: str, default_question: str, missing_param: str, collected_params: dict) -> str:
        fallback = default_question
        if not self.llm.is_available() and not self.llm.config.strict_mode:
            return fallback

        rendered = self.llm.safe_complete(
            ACTION_FOLLOW_UP_SYSTEM_PROMPT,
            (
                f"Tool name: {tool_name}\n"
                f"Missing parameter: {missing_param}\n"
                f"Collected parameters: {collected_params}\n"
                f"Default follow-up question: {default_question}\n\n"
                "Ask the student for the missing information."
            ),
            fallback=fallback,
        ).strip()
        if not rendered:
            return fallback
        if tool_name == "appointment_booking":
            lowered = normalize_user_text(rendered)
            invalid_phrases = {
                "assistant noted",
                "i noted your preference",
                "i have recorded",
                "i've recorded",
                "recorded your preference",
            }
            required_keywords = {
                "name": {"name"},
                "student_status": {"newly admitted", "incoming", "current"},
                "contact_details": {"contact", "email"},
                "topic": {"appointment", "about", "topic"},
                "appointment_format": {"in-person", "phone", "video", "preference", "online"},
                "folio_access": {"folio", "yes", "no", "not sure"},
            }
            if any(phrase in lowered for phrase in invalid_phrases):
                return fallback
            if "?" not in rendered:
                return fallback
            if not any(keyword in lowered for keyword in required_keywords.get(missing_param, set())):
                return fallback
        return rendered

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
            response_mode = "action_follow_up_llm" if self.llm.is_available() else "action_follow_up_template"
            follow_up = self._render_follow_up(
                tool.name,
                tool.follow_up_for(missing[0]),
                missing[0],
                session.collected_params,
            )
            self._save_session(session)
            return AgentResponse(
                answer=follow_up,
                intent="action",
                follow_up_question=follow_up,
                tool_name=tool.name,
                metadata={"missing_params": missing, "response_mode": response_mode},
            )

        result = tool.run(params, request_text=message, history=session.history)
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
            metadata={**result.metadata, "response_mode": "action_tool_grounded_kb"},
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
            response = AgentResponse(
                answer=answer,
                intent="knowledge",
                guardrails=guardrails,
                metadata={"response_mode": "static_guardrail"},
            )
            return session_id, self._finalize_response(session, answer, response)
        if is_capability_question(normalized_message):
            answer = self._capabilities_response()
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(
                answer=answer,
                intent="knowledge",
                guardrails=guardrails,
                metadata={"response_mode": "static_guardrail"},
            )
            return session_id, self._finalize_response(session, answer, response)
        if session.history and self._is_memory_recall_query(sanitized_message):
            self._update_session_title(session, message)
            session.history.append(ChatMessage(role="user", content=message))
            memory_answer = self._memory_recall_response(session, sanitized_message)
            response = AgentResponse(
                answer=memory_answer or "I don't have that earlier in this session.",
                intent="knowledge",
                guardrails=guardrails,
                metadata={"response_mode": "session_memory"},
            )
            return session_id, self._finalize_response(session, response.answer, response)
        if is_out_of_scope_query(normalized_message):
            answer = "I can only help with University of Toronto CIE and international student support topics."
            self._update_session_title(session, message)
            session.history.append(ChatMessage(role="user", content=message))
            response = AgentResponse(
                answer=answer,
                intent="out_of_scope",
                guardrails=guardrails,
                metadata={"response_mode": "static_guardrail"},
            )
            return session_id, self._finalize_response(session, answer, response)

        self._update_session_title(session, message)
        session.history.append(ChatMessage(role="user", content=message))

        if session.active_tool:
            if self._is_active_tool_status_query(sanitized_message):
                status_answer = self._render_active_tool_status(session)
                response = AgentResponse(
                    answer=status_answer,
                    intent="action",
                    tool_name=session.active_tool,
                    guardrails=guardrails,
                    metadata={"response_mode": "action_status", "missing_params": session.missing_params},
                )
                return session_id, self._finalize_response(session, status_answer, response)

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
            response = AgentResponse(
                answer=answer,
                intent="out_of_scope",
                guardrails=guardrails,
                metadata={"response_mode": "intent_out_of_scope"},
            )
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
                response_mode = "action_follow_up_llm" if self.llm.is_available() else "action_follow_up_template"
                follow_up = self._render_follow_up(
                    tool.name,
                    tool.follow_up_for(missing[0]),
                    missing[0],
                    session.collected_params,
                )
                self._save_session(session)
                response = AgentResponse(
                    answer=follow_up,
                    intent="action",
                    follow_up_question=follow_up,
                    tool_name=tool.name,
                    guardrails=guardrails,
                    metadata={"missing_params": missing, "response_mode": response_mode},
                )
                return session_id, self._finalize_response(session, follow_up, response)

            response = self._handle_tool_turn(session, sanitized_message)
            response.guardrails.extend(guardrails)
            return session_id, self._finalize_response(session, response.answer, response)

        answer, sources, retrieval_query = self.rag.answer(normalized_message, history=session.history[:-1])
        if needs_immigration_disclaimer(message) or needs_immigration_disclaimer(answer):
            answer = self._append_immigration_disclaimer(answer, guardrails)

        response_mode = "rag_llm" if self.llm.is_available() else "rag_fallback"
        response = AgentResponse(
            answer=answer,
            intent="knowledge",
            sources=sources,
            guardrails=guardrails,
            metadata={"retrieval_query": retrieval_query, "response_mode": response_mode},
        )
        return session_id, self._finalize_response(session, answer, response)
