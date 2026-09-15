"""Disposable Docker execution for generated candidates."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from axiomrunner.domain import (
    Candidate,
    ChallengeProblem,
    CheckResult,
    CheckStatus,
    JsonValue,
    SandboxLimits,
)
from axiomrunner.errors import RuntimeUnavailableError
from axiomrunner.static_validation import extract_source

IMAGE = "python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea"


@dataclass(frozen=True, slots=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


ProcessRunner = Callable[[Sequence[str], float], ProcessResult]


def _run_process(command: Sequence[str], timeout_s: float) -> ProcessResult:
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return ProcessResult(124, "", "sandbox timeout")
    except OSError as error:
        raise RuntimeUnavailableError(f"Docker execution failed: {type(error).__name__}") from error
    return ProcessResult(completed.returncode, completed.stdout, completed.stderr)


class DockerSandbox:
    """Execute import and example checks in a constrained Python container."""

    def __init__(
        self,
        limits: SandboxLimits,
        *,
        image: str = IMAGE,
        runner: ProcessRunner = _run_process,
    ) -> None:
        self.limits = limits
        self.image = image
        self._runner = runner

    def verify(self, candidate: Candidate, problem: ChallengeProblem) -> CheckResult:
        started = time.monotonic()
        docker = shutil.which("docker")
        if docker is None and self._runner is _run_process:
            raise RuntimeUnavailableError("docker executable not found")
        with tempfile.TemporaryDirectory(prefix="axiomrunner-") as raw_directory:
            directory = Path(raw_directory)
            (directory / "candidate.py").write_text(
                extract_source(candidate.source), encoding="utf-8"
            )
            (directory / "examples.json").write_text(
                json.dumps(list(problem.public_examples), ensure_ascii=False), encoding="utf-8"
            )
            (directory / "runner.py").write_text(RUNNER_SOURCE, encoding="utf-8")
            directory.chmod(0o755)
            mount = f"{directory.resolve()}:/work:ro"
            command = [
                docker or "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--memory",
                f"{self.limits.memory_mb}m",
                "--cpus",
                str(self.limits.cpus),
                "--pids-limit",
                str(self.limits.processes),
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                "65534:65534",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=16m",
                "-v",
                mount,
                "-w",
                "/work",
                self.image,
                "python",
                "-I",
                "runner.py",
                problem.entrypoint,
            ]
            result = self._runner(command, self.limits.timeout_s)
        elapsed = max(0.0, time.monotonic() - started)
        if result.returncode != 0:
            details: dict[str, JsonValue] = {
                "returncode": result.returncode,
                "stderr": result.stderr[-2000:],
            }
            return CheckResult("sandbox", "docker", CheckStatus.FAILED, elapsed, details=details)
        try:
            payload = json.loads(result.stdout)
            passed = int(payload["passed"])
            total = int(payload["total"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            return CheckResult(
                "sandbox",
                "docker",
                CheckStatus.INCONCLUSIVE,
                elapsed,
                details={"error": f"invalid harness output: {type(error).__name__}"},
            )
        status = CheckStatus.PASSED if passed == total else CheckStatus.FAILED
        return CheckResult(
            "sandbox",
            "docker",
            status,
            elapsed,
            details={"passed": passed, "total": total, "failures": payload.get("failures", [])},
        )


RUNNER_SOURCE = r"""import importlib.util
import json
import sys


def main():
    entrypoint = sys.argv[1]
    spec = importlib.util.spec_from_file_location("candidate", "/work/candidate.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load candidate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, entrypoint)
    if not callable(function):
        raise TypeError("entrypoint is not callable")
    with open("/work/examples.json", encoding="utf-8") as stream:
        examples = json.load(stream)
    failures = []
    for index, example in enumerate(examples):
        if not isinstance(example, dict):
            failures.append({"index": index, "error": "example must be an object"})
            continue
        args = example.get("args", [])
        kwargs = example.get("kwargs", {})
        expected = example.get("expected", example.get("output"))
        try:
            actual = function(*args, **kwargs)
            encoded = json.loads(json.dumps(actual))
            if encoded != expected:
                failures.append({"index": index, "expected": expected, "actual": encoded})
        except Exception as error:
            failures.append({"index": index, "error": type(error).__name__})
    result = {"passed": len(examples) - len(failures), "total": len(examples), "failures": failures}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
"""
