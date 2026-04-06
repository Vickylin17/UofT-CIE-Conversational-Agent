from __future__ import annotations

import logging

import chromadb

from config import AppConfig
from data_pipeline.embeddings import BaseEmbeddingProvider
from schemas import ChunkRecord, RetrievedDocument


LOGGER = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self, config: AppConfig, embedding_provider: BaseEmbeddingProvider) -> None:
        self.config = config
        self.embedding_provider = embedding_provider
        self.client = chromadb.PersistentClient(path=str(config.paths.chroma_dir))
        self.collection = self.client.get_or_create_collection(name=config.retrieval.collection_name)

    def rebuild(self, chunks: list[ChunkRecord]) -> None:
        if self.collection.count() > 0:
            existing_ids = self.collection.get(include=[])["ids"]
            if existing_ids:
                self.collection.delete(ids=existing_ids)

        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_provider.embed_documents(texts)
        self.collection.add(
            ids=[chunk.id for chunk in chunks],
            documents=texts,
            metadatas=[
                {
                    "url": chunk.url,
                    "title": chunk.title,
                    "category": chunk.category,
                    "section": chunk.section,
                }
                for chunk in chunks
            ],
            embeddings=embeddings,
        )
        LOGGER.info("Indexed %d chunks into Chroma.", len(chunks))

    def retrieve(self, query: str, top_k: int) -> list[RetrievedDocument]:
        query_embedding = self.embedding_provider.embed_query(query)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        retrieved: list[RetrievedDocument] = []
        for doc_id, doc_text, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            score = 1 / (1 + distance) if distance is not None else None
            retrieved.append(
                RetrievedDocument(id=doc_id, content=doc_text, metadata=metadata or {}, score=score)
            )
        return retrieved
