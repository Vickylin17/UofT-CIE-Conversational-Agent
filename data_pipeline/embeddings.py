from __future__ import annotations

import os
from abc import ABC, abstractmethod

import numpy as np
from openai import OpenAI
from sklearn.feature_extraction.text import HashingVectorizer

from config import EmbeddingConfig
from exceptions import ConfigurationError


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, config: EmbeddingConfig) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY is required for OpenAI embeddings.")
        self.client = OpenAI(api_key=api_key)
        self.model = config.openai_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, config: EmbeddingConfig) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(config.model)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class HashingEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, dimensions: int = 768) -> None:
        self.vectorizer = HashingVectorizer(n_features=dimensions, alternate_sign=False, norm="l2")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        matrix = self.vectorizer.transform(texts)
        return np.asarray(matrix.todense()).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def build_embedding_provider(config: EmbeddingConfig) -> BaseEmbeddingProvider:
    provider = config.provider.lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider(config)
    if provider == "sentence-transformers":
        try:
            return SentenceTransformerEmbeddingProvider(config)
        except Exception:
            return HashingEmbeddingProvider()
    if provider == "hashing":
        return HashingEmbeddingProvider()
    raise ConfigurationError(f"Unsupported embedding provider: {config.provider}")
