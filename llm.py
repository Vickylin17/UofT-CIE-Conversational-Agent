from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from config import LLMConfig
from exceptions import ConfigurationError


LOGGER = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=BaseModel)


def _extract_json_block(text: str) -> str:
    fenced_match = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)

    brace_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if brace_match:
        return brace_match.group(1)
    return text


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.api_key = config.api_key or os.getenv("LLM_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv(
            "OPENAI_API_KEY", ""
        )
        self.base_url = config.base_url.rstrip("/")
        self.client = (
            OpenAI(api_key=self.api_key, base_url=self.base_url)
            if self.api_key and self.config.provider.lower() in {"openai-compatible", "openai"}
            else None
        )

    def is_available(self) -> bool:
        return self.client is not None and self.config.provider.lower() in {"openai-compatible", "openai"}

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    def complete(self, system_prompt: str, user_prompt: str, temperature: float | None = None) -> str:
        if not self.is_available():
            raise ConfigurationError(
                "No hosted LLM is configured. Set LLM_API_KEY or QWEN_API_KEY to enable the provided qwen endpoint."
            )

        response = self.client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature if temperature is None else temperature,
            max_tokens=self.config.max_output_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def complete_json(self, system_prompt: str, user_prompt: str, schema: type[ModelT]) -> ModelT:
        raw = self.complete(system_prompt, user_prompt, temperature=0.0)
        payload = json.loads(_extract_json_block(raw))
        return schema.model_validate(payload)

    def safe_complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[ModelT],
        fallback: ModelT,
    ) -> ModelT:
        if not self.is_available():
            return fallback
        try:
            return self.complete_json(system_prompt, user_prompt, schema)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Structured LLM call failed, using fallback: %s", exc)
            return fallback

    def safe_complete(self, system_prompt: str, user_prompt: str, fallback: str) -> str:
        if not self.is_available():
            return fallback
        try:
            return self.complete(system_prompt, user_prompt)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("LLM completion failed, using fallback: %s", exc)
            return fallback
