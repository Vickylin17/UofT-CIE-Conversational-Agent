from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent


def _default_session_store_path() -> Path:
    override = os.getenv("CIE_SESSION_STORE_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Application Support" / "UofT-CIE-Conversational-Agent" / "sessions.json"


@dataclass(slots=True)
class ScraperConfig:
    start_url: str = os.getenv(
        "CIE_START_URL",
        "https://internationalexperience.utoronto.ca/international-student-services/resource-and-information-hub",
    )
    allowed_domain: str = os.getenv("CIE_ALLOWED_DOMAIN", "internationalexperience.utoronto.ca")
    max_pages: int = int(os.getenv("CIE_MAX_PAGES", "80"))
    delay_seconds: float = float(os.getenv("CIE_DELAY_SECONDS", "1.0"))
    timeout_seconds: int = int(os.getenv("CIE_TIMEOUT_SECONDS", "20"))
    user_agent: str = os.getenv(
        "CIE_USER_AGENT",
        "UofT-CIE-RAG-Agent/1.0 (+https://internationalexperience.utoronto.ca/)",
    )
    extra_seed_urls: list[str] = field(
        default_factory=lambda: [
            seed.strip()
            for seed in os.getenv(
                "CIE_EXTRA_SEED_URLS",
                "https://internationalexperience.utoronto.ca/events",
            ).split(",")
            if seed.strip()
        ]
    )


@dataclass(slots=True)
class ChunkingConfig:
    chunk_size: int = int(os.getenv("CIE_CHUNK_SIZE", "650"))
    chunk_overlap: int = int(os.getenv("CIE_CHUNK_OVERLAP", "120"))


@dataclass(slots=True)
class EmbeddingConfig:
    provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")
    model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    openai_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


@dataclass(slots=True)
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai-compatible")
    model: str = os.getenv("LLM_MODEL", os.getenv("OPENAI_CHAT_MODEL", "qwen3-30b-a3b-fp8"))
    base_url: str = os.getenv("LLM_BASE_URL", "https://rsm-8430-finalproject.bjlkeng.io/v1")
    api_key: str = os.getenv("LLM_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.1")))
    max_output_tokens: int = int(
        os.getenv("LLM_MAX_OUTPUT_TOKENS", os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "700"))
    )


@dataclass(slots=True)
class RetrievalConfig:
    top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "cie_resource_hub")


@dataclass(slots=True)
class AppPaths:
    data_dir: Path = BASE_DIR / "data"
    raw_data_path: Path = BASE_DIR / "data" / "raw_data.json"
    cleaned_docs_path: Path = BASE_DIR / "data" / "cleaned_docs.json"
    evaluation_cases_path: Path = BASE_DIR / "evaluation" / "test_cases.json"
    evaluation_results_path: Path = BASE_DIR / "evaluation" / "results.json"
    session_store_path: Path = field(default_factory=_default_session_store_path)
    chroma_dir: Path = BASE_DIR / "chroma_db"


@dataclass(slots=True)
class AppConfig:
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embeddings: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    paths: AppPaths = field(default_factory=AppPaths)

    def ensure_directories(self) -> None:
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        self.paths.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.paths.evaluation_cases_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.session_store_path.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    config = AppConfig()
    config.ensure_directories()
    return config
