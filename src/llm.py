"""OpenAI-compatible chat client with bounded retries and usage accounting."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from openai import OpenAI

from config.runtime import LLMConfig


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    def add(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        self.calls += 1


class LLMClient:
    def __init__(self, config: LLMConfig, client: Any | None = None):
        self.config = config
        self.client = client or OpenAI(
            api_key=config.api_key, base_url=config.base_url, timeout=config.timeout_seconds
        )
        self.usage = Usage()

    def chat_text(self, messages: Sequence[Mapping[str, str]], *, temperature: float | None = None,
                  max_tokens: int | None = None) -> str:
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=list(messages),
                    temperature=self.config.temperature if temperature is None else temperature,
                    max_tokens=self.config.max_tokens if max_tokens is None else max_tokens,
                )
                self.usage.add(response)
                content = response.choices[0].message.content
                if content and content.strip():
                    return content.strip()
                raise RuntimeError("LLM returned an empty response")
            except Exception as error:
                last_error = error
                if attempt + 1 < self.config.max_retries:
                    time.sleep(2**attempt)
        raise RuntimeError(f"LLM request failed after {self.config.max_retries} attempts: {last_error}")

    def chat_json(self, messages: Sequence[Mapping[str, str]]) -> dict[str, Any]:
        text = self.chat_text(messages)
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError("LLM response did not contain a JSON object")
            value = json.loads(match.group(0))
        if not isinstance(value, dict):
            raise ValueError("LLM JSON response must be an object")
        return value
