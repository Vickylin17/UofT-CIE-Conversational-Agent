from __future__ import annotations

import re
from difflib import get_close_matches


DOMAIN_VOCAB = {
    "accept",
    "access",
    "admitted",
    "advising",
    "appointment",
    "appointments",
    "arrive",
    "arrived",
    "arriving",
    "arrival",
    "book",
    "booking",
    "canada",
    "checklist",
    "cie",
    "contact",
    "current",
    "email",
    "event",
    "events",
    "exchange",
    "folio",
    "format",
    "graduate",
    "health",
    "help",
    "immigration",
    "incoming",
    "individual",
    "insurance",
    "international",
    "issue",
    "permit",
    "phone",
    "planning",
    "pre",
    "prearrival",
    "roadmap",
    "session",
    "sessions",
    "soon",
    "status",
    "student",
    "study",
    "support",
    "travel",
    "uhip",
    "undergrad",
    "undergraduate",
    "utorid",
    "video",
    "visa",
}

PHRASE_NORMALIZATIONS: list[tuple[str, str]] = [
    (r"\bpre[\s-]*arrival\b", "pre arrival"),
    (r"\bu[\s-]*hip\b", "uhip"),
    (r"\bgrad student\b", "graduate student"),
    (r"\bundergrad student\b", "undergraduate student"),
    (r"\bindividual appt\b", "individual appointment"),
    (r"\bbook(?:ing)? an? individual appointment\b", "book individual appointment"),
]

ARRIVAL_STATUS_PATTERNS = {
    "already_in_canada": [
        "already in canada",
        "im in canada",
        "i'm in canada",
        "i am in canada",
        "in canada already",
    ],
    "arriving_soon": [
        "arriving soon",
        "arrive soon",
        "coming soon",
        "next week",
        "in two weeks",
        "in 2 weeks",
        "this month",
    ],
    "not_arrived": [
        "planning ahead",
        "not arrived",
        "havent arrived",
        "haven't arrived",
        "have not arrived",
        "before i arrive",
        "still planning",
        "not travelling yet",
        "not traveling yet",
    ],
}

STUDENT_TYPE_PATTERNS = {
    "undergraduate": ["undergraduate", "undergrad"],
    "graduate": ["graduate", "grad student", "masters", "phd"],
    "exchange": ["exchange", "visiting"],
    "other": ["other"],
}

BOOKING_PATTERNS = [
    "book individual appointment",
    "book appointment",
    "booking appointment",
    "make appointment",
    "schedule appointment",
    "individual appointment",
]


def _normalize_token(token: str) -> str:
    lowered = token.lower()
    if not lowered.isalpha() or len(lowered) < 4 or lowered in DOMAIN_VOCAB:
        return lowered

    match = get_close_matches(lowered, DOMAIN_VOCAB, n=1, cutoff=0.84)
    if not match:
        return lowered
    candidate = match[0]
    if abs(len(candidate) - len(lowered)) > 2:
        return lowered
    return candidate


def normalize_user_text(text: str) -> str:
    normalized = text.lower()
    for pattern, replacement in PHRASE_NORMALIZATIONS:
        normalized = re.sub(pattern, replacement, normalized)

    normalized = re.sub(r"[A-Za-z][A-Za-z']+", lambda match: _normalize_token(match.group(0)), normalized)
    normalized = normalized.replace("pre arrival", "pre-arrival")
    return " ".join(normalized.split())


def match_arrival_status(text: str) -> str | None:
    normalized = normalize_user_text(text)
    for status, patterns in ARRIVAL_STATUS_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            return status
    return None


def match_student_type(text: str) -> str | None:
    normalized = normalize_user_text(text)
    for student_type, patterns in STUDENT_TYPE_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            return student_type
    return None


def looks_like_booking_request(text: str) -> bool:
    normalized = normalize_user_text(text)
    return any(pattern in normalized for pattern in BOOKING_PATTERNS)


def is_brief_reply(text: str, max_words: int = 4) -> bool:
    return len(re.findall(r"\w+", normalize_user_text(text))) <= max_words
