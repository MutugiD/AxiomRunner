"""Host-safe structural validation for generated Python source."""

from __future__ import annotations

import ast
import re
import sys
import time

from axiomrunner.domain import Candidate, CheckResult, CheckStatus, JsonValue

FORBIDDEN_MODULES = {
    "ctypes",
    "ftplib",
    "http",
    "multiprocessing",
    "pathlib",
    "pickle",
    "shelve",
    "shutil",
    "socket",
    "subprocess",
    "tempfile",
    "urllib",
}
FORBIDDEN_CALLS = {"__import__", "breakpoint", "eval", "exec", "input", "open", "print"}
FORBIDDEN_ATTRIBUTES = {
    "connect",
    "popen",
    "remove",
    "removedirs",
    "rmdir",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "system",
    "unlink",
}
FENCE = re.compile(r"```(?:python|py)?\s*\n(?P<source>.*?)```", re.DOTALL | re.IGNORECASE)


def extract_source(value: str) -> str:
    """Accept plain source or one otherwise-empty Python fence."""
    if "```" not in value:
        return value.strip() + "\n"
    matches = list(FENCE.finditer(value))
    if len(matches) != 1:
        raise ValueError("candidate must contain exactly one Python code block")
    outside = value[: matches[0].start()] + value[matches[0].end() :]
    if outside.strip():
        raise ValueError("candidate contains text outside its Python code block")
    return matches[0].group("source").strip() + "\n"


class StaticVerifier:
    """Parse and inspect source without importing or executing it."""

    def verify(self, candidate: Candidate, entrypoint: str) -> tuple[CheckResult, ...]:
        started = time.monotonic()
        checks: list[CheckResult] = []
        try:
            source = extract_source(candidate.source)
        except ValueError as error:
            return (self._result("source", started, False, {"error": str(error)}),)

        try:
            tree = ast.parse(source, filename="candidate.py", mode="exec")
        except SyntaxError as error:
            return (
                self._result(
                    "syntax",
                    started,
                    False,
                    {"line": error.lineno or 0, "error": error.msg},
                ),
            )
        checks.append(self._result("syntax", started, True))

        entrypoints = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == entrypoint
        ]
        valid_entrypoint = len(entrypoints) == 1
        checks.append(
            self._result(
                "entrypoint",
                started,
                valid_entrypoint,
                {} if valid_entrypoint else {"error": "exactly one top-level function is required"},
            )
        )

        violations = tuple(sorted(set(_policy_violations(tree))))
        checks.append(
            self._result(
                "policy",
                started,
                not violations,
                {"violations": list(violations)} if violations else {},
            )
        )
        try:
            compile(tree, "candidate.py", "exec", dont_inherit=True)
            compiled = True
        except (SyntaxError, ValueError, TypeError) as error:
            compiled = False
            compile_error = str(error)
        checks.append(
            self._result(
                "compile",
                started,
                compiled,
                {} if compiled else {"error": compile_error},
            )
        )
        return tuple(checks)

    @staticmethod
    def _result(
        check_type: str,
        started: float,
        passed: bool,
        details: dict[str, JsonValue] | None = None,
    ) -> CheckResult:
        return CheckResult(
            check_type,
            "static",
            CheckStatus.PASSED if passed else CheckStatus.FAILED,
            max(0.0, time.monotonic() - started),
            details=details or {},
        )


def _policy_violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_import(alias.name, violations)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                violations.append("relative imports are forbidden")
            elif node.module:
                _check_import(node.module, violations)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                violations.append(f"call to {node.func.id} is forbidden")
            elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRIBUTES:
                violations.append(f"call to .{node.func.attr} is forbidden")
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "sys"
            and node.attr in {"stdin", "stdout", "stderr"}
        ):
            violations.append(f"access to sys.{node.attr} is forbidden")
    for node in tree.body:
        if not _safe_top_level(node):
            violations.append(f"top-level {type(node).__name__} is forbidden")
    return violations


def _check_import(module: str, violations: list[str]) -> None:
    root = module.partition(".")[0]
    if root not in sys.stdlib_module_names:
        violations.append(f"third-party import is forbidden: {root}")
    elif root in FORBIDDEN_MODULES:
        violations.append(f"dangerous import is forbidden: {root}")


def _safe_top_level(node: ast.stmt) -> bool:
    if isinstance(node, ast.FunctionDef | ast.ClassDef | ast.Import | ast.ImportFrom):
        return True
    if isinstance(node, ast.Expr):
        return isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    if isinstance(node, ast.Assign | ast.AnnAssign):
        value = node.value
        if value is None:
            return True
        try:
            ast.literal_eval(value)
        except (ValueError, TypeError):
            return False
        return True
    return False
