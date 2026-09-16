from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "axiomrunner_t4_acceptance.ipynb"


def _document() -> dict[str, object]:
    document = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_colab_notebook_is_clean_and_all_code_cells_compile() -> None:
    document = _document()
    assert document["nbformat"] == 4
    metadata = document["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["accelerator"] == "GPU"

    cells = document["cells"]
    assert isinstance(cells, list)
    for index, cell in enumerate(cells):
        assert isinstance(cell, dict)
        if cell["cell_type"] != "code":
            continue
        assert cell["execution_count"] is None
        assert cell["outputs"] == []
        source = "".join(cell["source"])
        compile(source, f"colab-cell-{index}", "exec")


def test_colab_notebook_preserves_release_controls() -> None:
    source = NOTEBOOK.read_text(encoding="utf-8")
    required_controls = (
        'MODEL = \\"qwen3:8b\\"',
        '\\"AXIOMRUNNER_CANDIDATES\\": \\"1\\"',
        '\\"AXIOMRUNNER_REPAIRS\\": \\"1\\"',
        '\\"AXIOMRUNNER_SEED\\": \\"7\\"',
        'languages != Counter({\\"python\\": 6, \\"rust\\": 4})',
        'document.get(\\"deadline_s\\") != 300.0',
        '\\"AXIOMRUNNER_DOCKER_TEST\\"',
        '\\"-m\\", \\"docker\\", \\"--no-cov\\"',
        'report.get(\\"solved\\") == 6',
        'report.get(\\"rejected_unsupported\\") == 4',
    )
    for control in required_controls:
        assert control in source


def test_colab_bundle_excludes_corpus_and_generated_solutions() -> None:
    document = _document()
    cells = document["cells"]
    assert isinstance(cells, list)
    code = "\n".join(
        "".join(cell["source"])
        for cell in cells
        if isinstance(cell, dict) and cell.get("cell_type") == "code"
    )
    assert "archive.write(path, arcname=path.name)" in code
    assert "for path in sorted(RESULTS.iterdir())" in code
    assert "CORPUS.iterdir()" not in code
    assert '"solution_source"' in code
    assert '"candidate_source"' in code
