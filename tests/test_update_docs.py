"""The docs generator must only ever touch text between its markers."""

import importlib.util
import json
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


def test_site_data_summarises_real_data_results(update_docs, tmp_path, monkeypatch):
    results, docs = tmp_path / "results", tmp_path / "docs"
    monkeypatch.setattr(update_docs, "ROOT", tmp_path)
    monkeypatch.setattr(update_docs, "RESULTS", results)
    monkeypatch.setattr(update_docs, "DOCS", docs)
    pass_all = "planet candidate (passes all tests)"
    validation = {
        "hosts": [
            {
                "host": "A",
                "detections": [
                    {"role": "candidate", "matches": "A b"},
                    {"role": "candidate", "matches": None},
                    {"role": "secondary", "matches": None},
                ],
            }
        ],
        "comparison": [
            {"recovered": True, "period_pct": -0.01, "rp_rs_pct": 2.0, "verdict": pass_all},
            {
                "recovered": True,
                "period_pct": 0.03,
                "rp_rs_pct": -4.0,
                "verdict": "likely false positive",
            },
            {"recovered": False},
        ],
    }
    candidates = {
        "candidates": [
            {"recovered": True, "verdict": pass_all},
            {"recovered": True, "verdict": "planet candidate (with caveats)"},
            {"recovered": False, "verdict": "not recovered by the search"},
        ]
    }
    grid = {"period_edges": [1, 2], "radius_edges": [1, 2], "recovered": [[1]], "total": [[2]]}
    injection = dict(
        grid,
        fraction=[[0.5]],
        n_injections=2,
        overall_fraction=0.5,
        base_lightcurve={"source": "TIC 7", "sectors": [1, 2], "masked_ephemerides": [[3, 1, 0.1]]},
    )
    for rel, data in (
        ("validation/validation.json", validation),
        ("candidates/candidates.json", candidates),
        ("injection_tic7/completeness.json", injection),
    ):
        (results / rel).parent.mkdir(parents=True, exist_ok=True)
        (results / rel).write_text(json.dumps(data))

    update_docs.site_data()
    stats = json.loads((docs / "_data/stats.json").read_text())
    assert stats["validation"] == {
        "n_hosts": 1,
        "n_planets": 3,
        "n_recovered": 2,
        "max_period_err_pct": 0.03,
        "median_rp_rs_err_pct": 3.0,
        "n_pass_all": 1,
        "n_false_positive": 1,
        "n_unmatched_detections": 1,
    }
    assert stats["candidates"] == {
        "n_tois": 3,
        "n_recovered": 2,
        "n_pass_all": 1,
        "n_caveats": 1,
        "n_false_positive": 0,
    }
    assert stats["completeness_real"]["overall_pct"] == 50.0
    real = json.loads((docs / "_data/completeness_real.json").read_text())
    assert real["label"] == "TIC 7, sectors 1, 2, known planets masked"
