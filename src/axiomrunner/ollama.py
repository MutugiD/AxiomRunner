"""Minimal loopback-only Ollama chat client with structured responses."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from axiomrunner.doctor import is_loopback_url
from axiomrunner.domain import JsonValue, ModelMetrics, to_json_value
from axiomrunner.errors import ModelProtocolError, RuntimeUnavailableError

Transport = Callable[[str, bytes, float], bytes]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class StructuredReply:
    content: dict[str, JsonValue]
    metrics: ModelMetrics


def _urlopen_transport(url: str, body: bytes, timeout: float) -> bytes:
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        return bytes(response.read())


class OllamaClient:
    """Send schema-constrained messages to one local model."""

    def __init__(
        self,
        host: str,
        model: str,
        *,
        seed: int = 7,
        transport: Transport = _urlopen_transport,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not is_loopback_url(host):
            raise ValueError("Ollama host must use HTTP loopback")
        if not model or model.endswith("-cloud") or ":cloud" in model:
            raise ValueError("Ollama model must be a non-cloud local model")
        self._url = f"{host.rstrip('/')}/api/chat"
        self.model = model
        self.seed = seed
        self._transport = transport
        self._clock = clock

    def chat(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, JsonValue],
        *,
        timeout_s: float,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> StructuredReply:
        if timeout_s <= 0:
            raise TimeoutError("model request has no remaining budget")
        normalized_schema = to_json_value(dict(schema))
        schema_instruction = "Return only JSON matching this schema exactly:\n" + json.dumps(
            normalized_schema, ensure_ascii=False, separators=(",", ":")
        )
        wire_messages = [{"role": item.role, "content": item.content} for item in messages]
        if wire_messages and wire_messages[0]["role"] == "system":
            wire_messages[0]["content"] += "\n" + schema_instruction
        else:
            wire_messages.insert(0, {"role": "system", "content": schema_instruction})
        payload = {
            "model": self.model,
            "messages": wire_messages,
            "stream": False,
            "think": False,
            "format": normalized_schema,
            "options": {
                "temperature": temperature,
                "seed": self.seed,
                "num_predict": max_tokens,
            },
            "keep_alive": "10m",
        }
        started = self._clock()
        try:
            raw = self._transport(
                self._url,
                json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout_s,
            )
        except (TimeoutError, HTTPError, URLError, OSError) as error:
            raise RuntimeUnavailableError(
                f"Ollama request failed: {type(error).__name__}"
            ) from error
        elapsed = max(0.0, self._clock() - started)
        try:
            envelope = json.loads(raw)
            content_text = envelope["message"]["content"]
            content = json.loads(content_text)
            if not isinstance(content, dict) or not all(isinstance(key, str) for key in content):
                raise TypeError("structured content must be an object")
            normalized = to_json_value(content)
            if not isinstance(normalized, dict):
                raise TypeError("structured content must be an object")
        except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
            raise ModelProtocolError("Ollama returned malformed structured content") from error
        duration_ns = envelope.get("total_duration")
        duration_s = duration_ns / 1_000_000_000 if isinstance(duration_ns, int) else elapsed
        metrics = ModelMetrics(
            duration_s=duration_s,
            prompt_tokens=_nonnegative_int(envelope.get("prompt_eval_count")),
            response_tokens=_nonnegative_int(envelope.get("eval_count")),
        )
        return StructuredReply(normalized, metrics)


def _nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0
