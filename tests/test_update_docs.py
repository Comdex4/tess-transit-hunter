"""The docs generator must only ever touch text between its markers."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_docs.py"


@pytest.fixture(scope="module")
def update_docs():
    spec = importlib.util.spec_from_file_location("update_docs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_replace_block_only_changes_marked_region(update_docs):
    text = "before\n<!-- BEGIN: x -->\nold\n<!-- END: x -->\nafter\n"
    out = update_docs.replace_block(text, "x", "new content\n")
    assert out == "before\n<!-- BEGIN: x -->\n\nnew content\n\n<!-- END: x -->\nafter\n"
    # Idempotent.
    assert update_docs.replace_block(out, "x", "new content\n") == out
    with pytest.raises(KeyError):
        update_docs.replace_block(text, "missing", "y")


def test_missing_results_produce_not_run_notice(update_docs, tmp_path, monkeypatch):
    monkeypatch.setattr(update_docs, "RESULTS", tmp_path)
    text = update_docs.validation_block(from_docs=True)
    assert text.startswith("> **Not yet run.**")
    assert "validate_known_planets.py" in text
    status = update_docs.status_block()
    assert status.count("**not yet run**") == 6
    assert status.count("needs network access") == 3


def test_status_when_every_analysis_has_run(update_docs, tmp_path, monkeypatch):
    monkeypatch.setattr(update_docs, "RESULTS", tmp_path)
    for rel in (
        "calibration/summary.json",
        "synthetic_benchmark/benchmark.json",
        "injection_synthetic/completeness.json",
        "validation/validation.json",
        "candidates/candidates.json",
        "injection_tic1/completeness.json",
    ):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("{}")
    status = update_docs.status_block()
    assert status.count("| done |") == 6
    assert "not yet run" not in status and "MAST" in status
