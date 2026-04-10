from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from config import LLMConfig
from exceptions import HostedLLMRequiredError, StructuredOutputError


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


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                continue
            item_type = getattr(item, "type", None)
            if item_type != "text":
                continue
            text_value = getattr(item, "text", "")
            if isinstance(text_value, str):
                parts.append(text_value)
            else:
                parts.append(str(getattr(text_value, "value", "")))
        return "".join(parts)
    return str(content or "")


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

    def require_available(self, purpose: str = "chat responses") -> None:
        if self.is_available():
            return
        raise HostedLLMRequiredError(
            f"The hosted LLM is required for {purpose}. "
            "Set LLM_API_KEY (or QWEN_API_KEY / OPENAI_API_KEY) to the course-provided token."
        )

    def _raw_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.require_available("chat completions")

        request_kwargs: dict[str, Any] = {
            "model": self.config.model,
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_output_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**request_kwargs)
        return _extract_text_content(response.choices[0].message.content).strip()

    def _parse_json_payload(self, raw: str) -> Any:
        candidates: list[str] = []
        stripped = raw.strip()
        if stripped:
            candidates.append(stripped)

        extracted = _extract_json_block(raw).strip()
        if extracted and extracted not in candidates:
            candidates.append(extracted)

        first_object_start = raw.find("{")
        last_object_end = raw.rfind("}")
        if first_object_start != -1 and last_object_end != -1 and last_object_end > first_object_start:
            object_slice = raw[first_object_start : last_object_end + 1].strip()
            if object_slice and object_slice not in candidates:
                candidates.append(object_slice)

        first_array_start = raw.find("[")
        last_array_end = raw.rfind("]")
        if first_array_start != -1 and last_array_end != -1 and last_array_end > first_array_start:
            array_slice = raw[first_array_start : last_array_end + 1].strip()
            if array_slice and array_slice not in candidates:
                candidates.append(array_slice)

        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        preview = stripped[:240] if stripped else "<empty response>"
        raise StructuredOutputError(f"Hosted LLM did not return valid JSON. Raw response preview: {preview}")

    def _validate_json_response(self, raw: str, schema: type[ModelT]) -> ModelT:
        payload = self._parse_json_payload(raw)
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            preview = raw.strip()[:240] if raw.strip() else "<empty response>"
            raise StructuredOutputError(
                f"Hosted LLM returned JSON that did not match the expected schema. Raw response preview: {preview}"
            ) from exc

    def _json_repair_prompt(self, raw: str, schema: type[ModelT]) -> tuple[str, str]:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=True)
        system_prompt = (
            "You repair model outputs into strict JSON. "
            "Return only valid JSON that matches the target schema. "
            "Do not include markdown fences, commentary, or extra text."
        )
        user_prompt = (
            f"Target schema:\n{schema_json}\n\n"
            f"Invalid model output:\n{raw or '<empty response>'}\n\n"
            "Return only repaired JSON."
        )
        return system_prompt, user_prompt

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    def complete(self, system_prompt: str, user_prompt: str, temperature: float | None = None) -> str:
        return self._raw_completion(system_prompt, user_prompt, temperature=temperature)

    def complete_json(self, system_prompt: str, user_prompt: str, schema: type[ModelT]) -> ModelT:
        attempts: list[tuple[str, str, dict[str, Any] | None, str]] = [
            (
                system_prompt,
                user_prompt,
                {"type": "json_object"},
                "native_json_mode",
            ),
            (
                (
                    f"{system_prompt}\n\n"
                    "Return strict JSON only. Do not include markdown fences, explanations, or any extra text."
                ),
                (
                    f"{user_prompt}\n\n"
                    f"Return a valid JSON object that matches this schema:\n{json.dumps(schema.model_json_schema(), ensure_ascii=True)}"
                ),
                None,
                "prompt_only_json_retry",
            ),
        ]

        last_error: Exception | None = None
        last_raw = ""
        for attempt_system, attempt_user, response_format, label in attempts:
            try:
                raw = self._raw_completion(
                    attempt_system,
                    attempt_user,
                    temperature=0.0,
                    response_format=response_format,
                )
                last_raw = raw
                return self._validate_json_response(raw, schema)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                LOGGER.warning("Structured LLM attempt failed (%s): %s", label, exc)

        repair_system, repair_user = self._json_repair_prompt(last_raw, schema)
        try:
            repaired_raw = self._raw_completion(repair_system, repair_user, temperature=0.0, response_format={"type": "json_object"})
            return self._validate_json_response(repaired_raw, schema)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Structured LLM repair attempt failed: %s", exc)
            if isinstance(last_error, StructuredOutputError):
                raise last_error
            raise StructuredOutputError("Hosted LLM did not return usable structured output.") from exc

    def safe_complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[ModelT],
        fallback: ModelT,
    ) -> ModelT:
        if self.config.strict_mode:
            try:
                return self.complete_json(system_prompt, user_prompt, schema)
            except StructuredOutputError as exc:
                LOGGER.warning("Structured LLM call failed after JSON repair, using fallback: %s", exc)
                return fallback
        if not self.is_available():
            return fallback
        try:
            return self.complete_json(system_prompt, user_prompt, schema)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Structured LLM call failed, using fallback: %s", exc)
            return fallback

    def safe_complete(self, system_prompt: str, user_prompt: str, fallback: str) -> str:
        if self.config.strict_mode:
            return self.complete(system_prompt, user_prompt)
        if not self.is_available():
            return fallback
        try:
            return self.complete(system_prompt, user_prompt)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("LLM completion failed, using fallback: %s", exc)
            return fallback
