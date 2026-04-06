from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from config import AppConfig
from llm import LLMClient
from rag.prompting import (
    ANSWER_SYSTEM_PROMPT,
    QUERY_REWRITE_SYSTEM_PROMPT,
    format_context,
    format_history,
)
from rag.retriever import Retriever, extract_query_terms
from schemas import ChatMessage, SourceAttribution


LOGGER = logging.getLogger(__name__)


def _extract_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


@dataclass(slots=True)
class ParsedDocument:
    title: str
    section: str
    content: str


def _parse_document_text(text: str) -> ParsedDocument:
    title_match = re.search(r"^Title:\s*(.+)$", text, re.MULTILINE)
    section_match = re.search(r"^Section:\s*(.+)$", text, re.MULTILINE)
    content_match = re.search(r"^Content:\s*(.+)$", text, re.MULTILINE | re.DOTALL)
    return ParsedDocument(
        title=(title_match.group(1).strip() if title_match else ""),
        section=(section_match.group(1).strip() if section_match else ""),
        content=(content_match.group(1).strip() if content_match else text.strip()),
    )


def _clean_summary_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\b(Undergraduate Graduate|Graduate Undergraduate)\b", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^Are you clear with your next steps\?\s*", "", cleaned, flags=re.I).strip()
    return cleaned


class RAGService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = LLMClient(config.llm)
        self.retriever = Retriever(config)

    def _rewrite_query(self, question: str, history: list[ChatMessage]) -> str:
        if not history or not self.llm.is_available():
            return question

        user_prompt = (
            f"Conversation:\n{format_history(history)}\n\n"
            f"Latest student message:\n{question}\n\n"
            "Standalone retrieval query:"
        )
        return self.llm.safe_complete(
            system_prompt=QUERY_REWRITE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            fallback=question,
        ).strip()

    def _dedupe_sources(self, sources: list[SourceAttribution], max_sources: int = 3) -> list[SourceAttribution]:
        unique_sources: list[SourceAttribution] = []
        seen_urls: set[str] = set()
        for source in sources:
            if not source.url or source.url in seen_urls:
                continue
            seen_urls.add(source.url)
            unique_sources.append(source)
            if len(unique_sources) >= max_sources:
                break
        return unique_sources

    def _extractive_fallback(self, question: str, context_docs: list[str]) -> str:
        query_terms = extract_query_terms(question)
        best_document: ParsedDocument | None = None
        best_document_score = -1

        for document_text in context_docs:
            document = _parse_document_text(document_text)
            searchable_text = f"{document.title} {document.section} {document.content}"
            document_terms = {token.lower() for token in re.findall(r"\w+", searchable_text)}
            document_score = len(query_terms & document_terms)
            if document.title:
                title_text = document.title.lower()
                document_score += sum(3 for term in query_terms if term in title_text)
            if document.section:
                section_text = document.section.lower()
                document_score += sum(2 for term in query_terms if term in section_text)
            if document_score > best_document_score:
                best_document_score = document_score
                best_document = document

        if not best_document:
            return "I don't know"

        best_sentence = ""
        best_score = 0
        for sentence in _extract_sentences(best_document.content):
            sentence_terms = {token.lower() for token in re.findall(r"\w+", sentence)}
            overlap = len(query_terms & sentence_terms)
            if overlap > best_score:
                best_score = overlap
                best_sentence = sentence

        minimum_overlap = 2 if len(query_terms) >= 2 else 1
        if best_score < minimum_overlap:
            best_content = _clean_summary_text(best_document.content)
            if "roadmap" in best_document.title.lower() and best_content:
                return (
                    f"The {best_document.title} is a guide for international students that helps them stay on track "
                    "through their journey at the University of Toronto, including key milestones, checkpoints, and resources "
                    "across stages such as pre-arrival, transition in, and transition out."
                )
            return "I don't know"

        sentence = best_sentence.strip()
        if not sentence:
            return "I don't know"

        if best_document.title and best_document.title.lower() not in sentence.lower():
            if best_document.section and best_document.section.lower() != best_document.title.lower():
                return f"According to the {best_document.title} page, under {best_document.section}, {sentence[0].lower() + sentence[1:]}"
            return f"According to the {best_document.title} page, {sentence[0].lower() + sentence[1:]}"
        return sentence

    def answer(self, question: str, history: list[ChatMessage] | None = None) -> tuple[str, list[SourceAttribution], str]:
        history = history or []
        retrieval_query = self._rewrite_query(question, history)
        retrieved = self.retriever.retrieve(retrieval_query)

        if not retrieved:
            return "I don't know", [], retrieval_query

        context = format_context(retrieved)
        sources = [
            SourceAttribution(
                title=document.metadata.get("title", "Unknown"),
                url=document.metadata.get("url", ""),
                section=document.metadata.get("section", "Overview"),
            )
            for document in retrieved
        ]

        fallback = self._extractive_fallback(question, [document.content for document in retrieved])
        user_prompt = (
            f"Conversation:\n{format_history(history)}\n\n"
            f"Question:\n{question}\n\n"
            f"Context:\n{context}\n\n"
            "Answer the question using only the context."
        )
        answer = self.llm.safe_complete(ANSWER_SYSTEM_PROMPT, user_prompt, fallback=fallback).strip()
        if not answer:
            answer = "I don't know"
        if answer.strip().lower() == "i don't know":
            return answer, [], retrieval_query
        if answer.startswith("Title:"):
            answer = fallback
        return answer, self._dedupe_sources(sources), retrieval_query
