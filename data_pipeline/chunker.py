from __future__ import annotations

import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import ChunkingConfig
from schemas import ChunkRecord, CleanDocument


def build_chunks(docs: list[CleanDocument], config: ChunkingConfig) -> list[ChunkRecord]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[ChunkRecord] = []

    for doc in docs:
        for section_index, section in enumerate(doc.sections):
            prefix = f"Title: {doc.title}\nCategory: {doc.category}\nSection: {section.heading}\nContent: "
            parts = splitter.split_text(section.content)
            for index, part in enumerate(parts):
                text = f"{prefix}{part}".strip()
                digest = hashlib.md5(
                    f"{doc.url}|{section_index}|{section.heading}|{index}|{part}".encode("utf-8")
                ).hexdigest()
                chunks.append(
                    ChunkRecord(
                        id=digest,
                        text=text,
                        url=doc.url,
                        title=doc.title,
                        category=doc.category,
                        section=section.heading,
                    )
                )
    return chunks
