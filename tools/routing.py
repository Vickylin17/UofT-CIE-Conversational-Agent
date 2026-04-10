from __future__ import annotations

from tools.base import KnowledgeBackedActionTool, ToolParameter


class SupportRoutingTool(KnowledgeBackedActionTool):
    name = "support_routing"
    description = "Route a student to the most relevant CIE support service."
    parameters = [
        ToolParameter(
            name="user_query",
            description="The student support question.",
            follow_up_question="What would you like help with so I can route you to the right CIE service?",
        )
    ]

    def missing_params(self, provided: dict[str, str]) -> list[str]:
        query = (provided.get("user_query") or "").strip().lower()
        if not query:
            return ["user_query"]
        generic_queries = {
            "i need help",
            "help me",
            "support",
            "i need support",
            "can you help",
        }
        if query in generic_queries or len(query.split()) <= 2:
            return ["user_query"]
        return []

    def run(self, params: dict[str, str], request_text: str = "", history=None):
        user_query = params.get("user_query", "").strip() or request_text.strip()
        question = (
            "A student wants to know where to get help from CIE.\n"
            f"Student request: {user_query}\n\n"
            "Using only the CIE knowledge base, identify the most relevant CIE page, service, or support starting point. "
            "Explain why it fits and suggest the best next step. Cite only information grounded in the knowledge base."
        )
        return self._grounded_answer(
            question,
            retrieval_query=user_query,
            history=history,
            metadata={"needs_disclaimer": False, "tool_mode": "knowledge_grounded_routing"},
        )
