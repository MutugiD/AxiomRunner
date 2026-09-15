import pytest

from axiomrunner.config import ConfigurationError, load_options


def test_defaults_are_local_and_bounded() -> None:
    options = load_options({})
    assert options.model == "qwen3:8b"
    assert options.ollama_host == "http://127.0.0.1:11434"
    assert options.candidate_limit == 3


def test_environment_overrides_non_secret_options() -> None:
    options = load_options(
        {
            "AXIOMRUNNER_MODEL": "qwen3:1.7b",
            "AXIOMRUNNER_CANDIDATES": "1",
            "AXIOMRUNNER_REPAIRS": "0",
            "AXIOMRUNNER_MEMORY_MB": "512",
        }
    )
    assert options.model == "qwen3:1.7b"
    assert options.candidate_limit == 1
    assert options.repair_limit == 0
    assert options.sandbox.memory_mb == 512


@pytest.mark.parametrize("value", ["not-a-number", "0", "-2"])
def test_invalid_candidate_limit_is_rejected(value: str) -> None:
    with pytest.raises(ConfigurationError):
        load_options({"AXIOMRUNNER_CANDIDATES": value})
