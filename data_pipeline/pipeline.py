from __future__ import annotations

import logging

from config import AppConfig
from data_pipeline.chunker import build_chunks
from data_pipeline.cleaner import clean_document
from data_pipeline.embeddings import build_embedding_provider
from data_pipeline.extractor import extract_document
from data_pipeline.io_utils import write_json
from data_pipeline.scraper import crawl_site
from data_pipeline.vector_store import ChromaVectorStore


LOGGER = logging.getLogger(__name__)


def run_pipeline(config: AppConfig) -> dict[str, int]:
    pages = crawl_site(config.scraper)
    raw_docs = [extract_document(url, html) for url, html in pages.items()]
    clean_docs = [clean_document(doc) for doc in raw_docs]
    chunks = build_chunks(clean_docs, config.chunking)

    write_json(config.paths.raw_data_path, [doc.model_dump() for doc in raw_docs])
    write_json(config.paths.cleaned_docs_path, [doc.model_dump() for doc in clean_docs])

    embedding_provider = build_embedding_provider(config.embeddings)
    vector_store = ChromaVectorStore(config, embedding_provider)
    vector_store.rebuild(chunks)

    stats = {"pages": len(raw_docs), "documents": len(clean_docs), "chunks": len(chunks)}
    LOGGER.info("Pipeline complete: %s", stats)
    return stats
