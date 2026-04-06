from __future__ import annotations

import re

from config import AppConfig
from data_pipeline.io_utils import read_json
from data_pipeline.embeddings import HashingEmbeddingProvider, build_embedding_provider
from data_pipeline.vector_store import ChromaVectorStore
from schemas import RetrievedDocument


STOPWORDS = {
    "what",
    "does",
    "the",
    "say",
    "about",
    "with",
    "for",
    "from",
    "this",
    "that",
    "have",
    "into",
    "your",
    "will",
    "where",
    "when",
    "which",
    "there",
    "resource",
    "hub",
    "information",
}


def extract_query_terms(query: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\w+", query)
        if len(token) > 2 and token.lower() not in STOPWORDS
    }


class Retriever:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.embedding_provider = build_embedding_provider(config.embeddings)
        self.vector_store = ChromaVectorStore(config, self.embedding_provider)
        self.cleaned_docs = read_json(config.paths.cleaned_docs_path, default=[])

    def _lexical_retrieve(self, query: str, top_k: int) -> list[RetrievedDocument]:
        query_terms = extract_query_terms(query)
        if not query_terms:
            return []

        matches: list[tuple[float, RetrievedDocument]] = []
        for doc in self.cleaned_docs:
            title = doc.get("title", "")
            category = doc.get("category", "")
            for section in doc.get("sections", []):
                heading = section.get("heading", "Overview")
                content = section.get("content", "")
                haystack = f"{title} {category} {heading} {content}".lower()
                overlap = sum(1 for term in query_terms if term in haystack)
                if overlap == 0:
                    continue
                score = overlap * 3
                if any(term in title.lower() for term in query_terms):
                    score += 6
                if any(term in heading.lower() for term in query_terms):
                    score += 3
                text = f"Title: {title}\nCategory: {category}\nSection: {heading}\nContent: {content}"
                matches.append(
                    (
                        float(score),
                        RetrievedDocument(
                            id=f"lexical::{doc['url']}::{heading}::{len(matches)}",
                            content=text,
                            metadata={
                                "url": doc["url"],
                                "title": title,
                                "category": category,
                                "section": heading,
                            },
                            score=float(score),
                        ),
                    )
                )

        matches.sort(key=lambda item: item[0], reverse=True)
        return [match[1] for match in matches[:top_k]]

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedDocument]:
        k = top_k or self.config.retrieval.top_k
        lexical_results = self._lexical_retrieve(query, top_k=max(k * 2, 8))
        if isinstance(self.embedding_provider, HashingEmbeddingProvider):
            return lexical_results[:k]

        semantic_results = self.vector_store.retrieve(query=query, top_k=max(k * 2, 8))

        merged: list[RetrievedDocument] = []
        seen: set[str] = set()
        for document in sorted(
            [*semantic_results, *lexical_results],
            key=lambda item: item.score if item.score is not None else 0.0,
            reverse=True,
        ):
            key = f"{document.metadata.get('url')}::{document.metadata.get('section')}::{document.content[:80]}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(document)
            if len(merged) >= k:
                break
        return merged
