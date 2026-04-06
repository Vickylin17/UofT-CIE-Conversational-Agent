from __future__ import annotations

import re


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
    lowered = text.lower()
    return any(keyword in lowered for keyword in OUT_OF_SCOPE_KEYWORDS)


def is_greeting(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    return lowered in GREETING_TERMS


def is_capability_question(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    return any(pattern in lowered for pattern in CAPABILITY_PATTERNS)


def needs_immigration_disclaimer(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in IMMIGRATION_TERMS)


def immigration_disclaimer() -> str:
    return "Note: This is not legal advice. For case-specific immigration questions, please confirm details with a CIE advisor."
