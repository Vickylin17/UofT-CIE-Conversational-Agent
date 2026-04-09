from __future__ import annotations

from tools.base import ActionTool, ToolParameter
from schemas import SourceAttribution, ToolResult


ROUTING_RULES = {
    "immigration": {
        "keywords": ["study permit", "visa", "immigration", "work permit", "trv", "pgwp"],
        "service": "Immigration Advising",
        "reason": "This page explains how CIE supports immigration questions such as study permits, visas, work authorization, and related status documents.",
        "next_step": "Start with the Immigration page and use it to find advising information and official guidance.",
        "title": "Immigration",
        "url": "https://internationalexperience.utoronto.ca/international-student-services/immigration",
        "section": "What CIE can and cannot do",
    },
    "uhip": {
        "keywords": ["uhip", "insurance", "clinic", "health coverage", "doctor"],
        "service": "UHIP and Health Insurance Support",
        "reason": "This page covers UHIP enrollment, cards, coverage, important dates, and health insurance guidance.",
        "next_step": "Start with the main UHIP page, then use its sections for onboarding, coverage, and status changes.",
        "title": "University Health Insurance Plan (UHIP)",
        "url": "https://internationalexperience.utoronto.ca/international-student-services/healthcare-coverage-and-u-of-t/university-health-insurance-plan-uhip",
        "section": "University Health Insurance Plan (UHIP)",
    },
    "finances": {
        "keywords": ["money", "bank", "finance", "tuition", "budget", "cost"],
        "service": "Resource Hub Finances Support",
        "reason": "They can help with financial planning topics such as budgeting, banking, and funding-related resources.",
        "next_step": "Review the Finances resources and student support referrals in the hub.",
        "title": "Finances",
        "url": "https://internationalexperience.utoronto.ca/international-student-services/resource-and-information-hub",
        "section": "Finances",
    },
    "peer_support": {
        "keywords": ["lonely", "friends", "stress", "peer", "support", "community"],
        "service": "Student Peer Support",
        "reason": "They can help with adjustment, community, belonging, and peer connection questions.",
        "next_step": "Check Student Peer Support offerings and community-based supports in the hub.",
    },
    "events": {
        "keywords": ["events", "event", "workshop", "session", "orientation", "programs"],
        "service": "Programs and Events",
        "reason": "This page lists current CIE programs, workshops, and event registration information.",
        "next_step": "Open the Programs & Events page to browse sessions, dates, and registration details.",
        "title": "Programs & Events",
        "url": "https://internationalexperience.utoronto.ca/events-programs",
        "section": "Programs & Events",
    },
}

DEFAULT_ROUTE = {
    "service": "Resource and Information Hub",
    "reason": "This looks like a general CIE support question rather than a specialized advising issue.",
    "next_step": "Start with the Resource and Information Hub or use the general contact page for tailored support.",
    "title": "Resource and Information Hub",
    "url": "https://internationalexperience.utoronto.ca/international-student-services/resource-and-information-hub",
    "section": "Overview",
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
            f"You can find this on the **{match['service']}** page.\n\n"
            f"{match['reason']}\n\n"
            f"Next step: {match['next_step']}"
        )
        sources = []
        if match.get("url"):
            sources.append(
                SourceAttribution(
                    title=str(match.get("title", match["service"])),
                    url=str(match["url"]),
                    section=str(match.get("section", "Overview")),
                )
            )
        return ToolResult(
            tool_name=self.name,
            output=output,
            sources=sources,
            metadata={
                "route": match["service"],
                "needs_disclaimer": False,
            },
        )
