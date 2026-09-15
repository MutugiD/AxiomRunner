import json

import pytest

from axiomrunner.errors import ModelProtocolError, RuntimeUnavailableError
from axiomrunner.ollama import ChatMessage, OllamaClient


def response(content: object, **metrics: int) -> bytes:
    return json.dumps({"message": {"content": json.dumps(content)}, **metrics}).encode()


def test_client_sends_schema_and_records_metrics() -> None:
    captured: dict[str, object] = {}

    def transport(url: str, body: bytes, timeout: float) -> bytes:
        captured.update(url=url, payload=json.loads(body), timeout=timeout)
        return response({"answer": "ok"}, total_duration=2_000_000_000, eval_count=8)

    client = OllamaClient("http://127.0.0.1:11434", "qwen3:8b", transport=transport)
    reply = client.chat(
        [ChatMessage("user", "hello")],
        {"type": "object"},
        timeout_s=3.0,
    )
    assert reply.content == {"answer": "ok"}
    assert reply.metrics.duration_s == 2.0
    assert reply.metrics.response_tokens == 8
    assert captured["timeout"] == 3.0
    assert captured["payload"]["format"] == {"type": "object"}  # type: ignore[index]
    assert captured["payload"]["think"] is False  # type: ignore[index]


@pytest.mark.parametrize(
    ("host", "model"),
    [("https://ollama.example.com", "qwen3:8b"), ("http://localhost:11434", "model:cloud")],
)
def test_client_rejects_remote_or_cloud_configuration(host: str, model: str) -> None:
    with pytest.raises(ValueError):
        OllamaClient(host, model)


def test_client_rejects_zero_timeout() -> None:
    client = OllamaClient("http://localhost:11434", "qwen3:8b", transport=lambda *_: b"")
    with pytest.raises(TimeoutError):
        client.chat([], {}, timeout_s=0)


@pytest.mark.parametrize("raw", [b"{}", b'{"message":{"content":"[]"}}', b"not-json"])
def test_client_rejects_malformed_responses(raw: bytes) -> None:
    client = OllamaClient("http://localhost:11434", "qwen3:8b", transport=lambda *_: raw)
    with pytest.raises(ModelProtocolError):
        client.chat([], {}, timeout_s=1)


def test_transport_failure_is_runtime_unavailable() -> None:
    def fail(*_: object) -> bytes:
        raise OSError("offline")

    client = OllamaClient("http://localhost:11434", "qwen3:8b", transport=fail)
    with pytest.raises(RuntimeUnavailableError):
        client.chat([], {}, timeout_s=1)
