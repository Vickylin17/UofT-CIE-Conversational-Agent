from __future__ import annotations

import re

from schemas import CleanDocument, PageSection, RawDocument


WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def clean_document(raw_doc: RawDocument) -> CleanDocument:
    cleaned_sections: list[PageSection] = []
    seen_signatures: set[str] = set()

    for section in raw_doc.sections:
        heading = normalize_whitespace(section.heading or "Overview")
        content = normalize_whitespace(section.content)
        if not content:
            continue

        signature = f"{heading.lower()}::{content.lower()}"
        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        cleaned_sections.append(PageSection(heading=heading, content=content))

    if not cleaned_sections:
        cleaned_sections.append(PageSection(heading="Overview", content=raw_doc.title))

    return CleanDocument(
        url=raw_doc.url,
        title=normalize_whitespace(raw_doc.title),
        category=normalize_whitespace(raw_doc.category or "General"),
        sections=cleaned_sections,
    )
