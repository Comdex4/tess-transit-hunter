"""The TOI-candidate script must only select stars whose own light curves exist."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "vet_toi_candidates.py"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("vet_toi_candidates", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeSearchResult:
    def __init__(self, target_names):
        self.table = {"target_name": target_names}

    def __len__(self):
        return len(self.table["target_name"])


@pytest.mark.parametrize(
    ("found", "expected"),
    [
        (["72090501", "72090501"], True),
        (["72090499", "72090499"], False),  # another catalogue entry at the same position
        ([], False),
    ],
)
def test_two_minute_data_must_belong_to_the_target(script, monkeypatch, found, expected):
    import lightkurve

    monkeypatch.setattr(lightkurve, "search_lightcurve", lambda *a, **k: FakeSearchResult(found))
    assert script.has_2min_data(72090501) is expected
