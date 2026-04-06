from __future__ import annotations

from tools.base import ActionTool, ToolParameter
from schemas import ToolResult


ROUTING_RULES = {
    "immigration": {
        "keywords": ["study permit", "visa", "immigration", "work permit", "trv", "pgwp"],
        "service": "Immigration Advising",
        "reason": "They can help with study permits, visas, work authorization, and related immigration documents.",
        "next_step": "Use the immigration resources page or contact a regulated international student advisor through CIE.",
    },
    "uhip": {
        "keywords": ["uhip", "insurance", "clinic", "health coverage", "doctor"],
        "service": "UHIP and Health Insurance Support",
        "reason": "They can help with UHIP coverage, enrollment, cards, and health insurance questions.",
        "next_step": "Start with the UHIP section in the Resource Hub and CIE health coverage guidance.",
    },
    "finances": {
        "keywords": ["money", "bank", "finance", "tuition", "budget", "cost"],
        "service": "Resource Hub Finances Support",
        "reason": "They can help with financial planning topics such as budgeting, banking, and funding-related resources.",
        "next_step": "Review the Finances resources and student support referrals in the hub.",
    },
    "peer_support": {
        "keywords": ["lonely", "friends", "stress", "peer", "support", "community"],
        "service": "Student Peer Support",
        "reason": "They can help with adjustment, community, belonging, and peer connection questions.",
        "next_step": "Check Student Peer Support offerings and community-based supports in the hub.",
    },
}

DEFAULT_ROUTE = {
    "service": "Resource and Information Hub",
    "reason": "This looks like a general CIE support question rather than a specialized advising issue.",
    "next_step": "Start with the Resource and Information Hub or use the general contact page for tailored support.",
}


class SupportRoutingTool(ActionTool):
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

    def run(self, params: dict[str, str]) -> ToolResult:
        query = params.get("user_query", "").lower()
        match = DEFAULT_ROUTE

        for rule in ROUTING_RULES.values():
            if any(keyword in query for keyword in rule["keywords"]):
                match = rule
                break

        output = (
            f"You should contact {match['service']}.\n\n"
            f"{match['reason']}\n\n"
            f"Next step: {match['next_step']}"
        )
        return ToolResult(
            tool_name=self.name,
            output=output,
            metadata={
                "route": match["service"],
                "needs_disclaimer": False,
            },
        )
