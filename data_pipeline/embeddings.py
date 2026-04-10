from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from urllib.parse import urlsplit, urlunsplit

import numpy as np
from openai import APIConnectionError, APIStatusError, APITimeoutError, InternalServerError, OpenAI
from sklearn.feature_extraction.text import HashingVectorizer

from config import EmbeddingConfig
from exceptions import ConfigurationError


LOGGER = logging.getLogger(__name__)


def _normalize_openai_base_url(base_url: str) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        return cleaned
    parts = urlsplit(cleaned)
    path = parts.path.rstrip("/")
    if not path:
        path = "/v1"
    elif not path.endswith("/v1"):
        path = f"{path}/v1"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        api_key = config.api_key
        if not api_key:
            raise ConfigurationError(
                "EMBEDDING_API_KEY is required for hosted embeddings. "
                "If you want to reuse the chat token, set LLM_API_KEY in the project .env file."
            )
        base_url = _normalize_openai_base_url(config.base_url)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = config.openai_model
        self.base_url = base_url
        self._fallback_provider: BaseEmbeddingProvider | None = None

    def _should_fallback(self, exc: Exception) -> bool:
        if isinstance(exc, (InternalServerError, APIConnectionError, APITimeoutError)):
            return True
        if isinstance(exc, APIStatusError):
            status_code = getattr(exc, "status_code", None)
            if status_code is None and getattr(exc, "response", None) is not None:
                status_code = getattr(exc.response, "status_code", None)
            return bool(status_code and int(status_code) >= 500)
        return False

    def _get_fallback_provider(self) -> BaseEmbeddingProvider:
        if self._fallback_provider is not None:
            return self._fallback_provider
        try:
            self._fallback_provider = SentenceTransformerEmbeddingProvider(self.config)
            LOGGER.warning(
                "Hosted embedding endpoint '%s' failed; falling back to local sentence-transformers embeddings.",
                self.base_url,
            )
        except Exception as fallback_exc:  # noqa: BLE001
            LOGGER.warning(
                "Hosted embedding endpoint '%s' failed and local sentence-transformers was unavailable; "
                "falling back to hashing embeddings: %s",
                self.base_url,
                fallback_exc,
            )
            self._fallback_provider = HashingEmbeddingProvider()
        return self._fallback_provider

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._fallback_provider is not None:
            return self._fallback_provider.embed_documents(texts)

        try:
            response = self.client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as exc:  # noqa: BLE001
            if not self._should_fallback(exc):
                raise
            LOGGER.warning("Hosted embeddings request failed: %s", exc)
            return self._get_fallback_provider().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if self._fallback_provider is not None:
            return self._fallback_provider.embed_query(text)
        return self.embed_documents([text])[0]


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, config: EmbeddingConfig) -> None:
        from sentence_transformers import SentenceTransformer

        # Avoid blocking app startup on Hugging Face download attempts. If the
        # model is not already cached locally, callers can fall back to hashing.
        self.model = SentenceTransformer(config.model, local_files_only=True)

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
    if provider in {"openai", "openai-compatible"}:
        return OpenAIEmbeddingProvider(config)
    if provider == "sentence-transformers":
        try:
            return SentenceTransformerEmbeddingProvider(config)
        except Exception as exc:
            LOGGER.warning(
                "SentenceTransformer model '%s' was not available locally; falling back to hashing embeddings: %s",
                config.model,
                exc,
            )
            return HashingEmbeddingProvider()
    if provider == "hashing":
        return HashingEmbeddingProvider()
    raise ConfigurationError(f"Unsupported embedding provider: {config.provider}")
