from __future__ import annotations

import re

from schemas import AgentResponse


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"\w+", text) if len(token) > 2}


def keyword_coverage(answer: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    answer_lower = answer.lower()
    matched = sum(1 for keyword in expected_keywords if keyword.lower() in answer_lower)
    return matched / len(expected_keywords)


def forbidden_keyword_penalty(answer: str, forbidden_keywords: list[str]) -> float:
    if not forbidden_keywords:
        return 1.0
    answer_lower = answer.lower()
    violations = sum(1 for keyword in forbidden_keywords if keyword.lower() in answer_lower)
    return max(0.0, 1 - (violations / len(forbidden_keywords)))


def faithfulness_score(answer: str, response: AgentResponse) -> float:
    if not response.sources:
        return 1.0 if answer.strip().lower() == "i don't know" else 0.3

    source_text = " ".join(
        f"{source.title} {source.section} {source.url}" for source in response.sources
    )
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0
    overlap = len(answer_tokens & _tokenize(source_text))
    return min(1.0, overlap / max(2, min(len(answer_tokens), 6)))


def context_precision(response: AgentResponse, expected_keywords: list[str]) -> float:
    if not response.sources or not expected_keywords:
        return 1.0
    keyword_hits = 0
    for source in response.sources:
        source_text = f"{source.title} {source.section} {source.url}".lower()
        if any(keyword.lower() in source_text for keyword in expected_keywords):
            keyword_hits += 1
    return keyword_hits / len(response.sources)
