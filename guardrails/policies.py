from __future__ import annotations

import re

from text_utils import looks_like_booking_request, normalize_user_text


PROMPT_INJECTION_PATTERNS = [
    r"ignore (all|any|the) previous instructions",
    r"system prompt",
    r"reveal .*prompt",
    r"developer message",
    r"act as",
]

OUT_OF_SCOPE_KEYWORDS = {
    "capital of france",
    "stock price",
    "recipe",
    "sorting algorithm",
    "movie review",
}

IMMIGRATION_TERMS = {"immigration", "study permit", "visa", "work permit", "pgwp", "trv"}
GREETING_TERMS = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}
CAPABILITY_PATTERNS = {
    "what can i ask",
    "what can you do",
    "how can you help",
    "what do you help with",
    "what should i ask",
    "when can you help",
    "can you help",
    "help",
}


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in PROMPT_INJECTION_PATTERNS)


def sanitize_user_input(text: str) -> str:
    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    return " ".join(sanitized.split()).strip() or text


def is_out_of_scope_query(text: str) -> bool:
    lowered = normalize_user_text(text)
    return any(keyword in lowered for keyword in OUT_OF_SCOPE_KEYWORDS)


def is_greeting(text: str) -> bool:
    lowered = normalize_user_text(text)
    cleaned = " ".join(re.sub(r"[^\w\s]", " ", lowered).split())
    return cleaned in GREETING_TERMS


def is_capability_question(text: str) -> bool:
    lowered = normalize_user_text(text)
    if looks_like_booking_request(lowered):
        return False

    if lowered in CAPABILITY_PATTERNS:
        return True

    generic_help_patterns = [
        r"^(what|how|when|where)\s+can\s+you\s+help\b",
        r"^can\s+you\s+help(?:\s+me)?\??$",
        r"^help(?:\s+me)?\??$",
    ]
    return any(re.search(pattern, lowered) for pattern in generic_help_patterns)


def needs_immigration_disclaimer(text: str) -> bool:
    lowered = normalize_user_text(text)
    return any(term in lowered for term in IMMIGRATION_TERMS)


def immigration_disclaimer() -> str:
    return "Note: This is not legal advice. For case-specific immigration questions, please confirm details with a CIE advisor."
