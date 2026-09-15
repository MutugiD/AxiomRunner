import pytest

from axiomrunner.candidates import CandidateRepository
from axiomrunner.domain import Candidate, CheckResult, CheckStatus


def test_repository_preserves_lineage_and_evidence_provenance() -> None:
    repository = CandidateRepository()
    parent = Candidate("parent", "strategy", "source")
    child = Candidate("child", "strategy", "repair", revision=1, parent_id="parent")
    repository.add(parent)
    repository.append("parent", (CheckResult("boundary", "test", CheckStatus.FAILED, 0),))
    repository.add(child)
    repository.append("child", (CheckResult("boundary", "test", CheckStatus.PASSED, 0),))
    assert repository.lineage("child") == (parent, child)
    assert [item.candidate_id for item in repository.provenance("child")] == ["parent", "child"]
    assert not repository.provenance("child")[0].viable
    assert repository.provenance("child")[1].viable


def test_repository_rejects_invalid_lineage() -> None:
    repository = CandidateRepository()
    with pytest.raises(ValueError, match="unknown parent"):
        repository.add(Candidate("child", "strategy", "source", revision=1, parent_id="missing"))
    repository.add(Candidate("root", "strategy", "source"))
    with pytest.raises(ValueError, match="immediately"):
        repository.add(Candidate("child", "strategy", "source", revision=2, parent_id="root"))
