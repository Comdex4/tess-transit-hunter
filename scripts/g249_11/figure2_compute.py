"""Figure 2 data: both passes of the pipeline's iterative BLS search on sectors 19, 59 and 60.

Calls `iterative_search` exactly as `pipeline.py` does (flattened light curve, the raw
light curve for re-detrending with found transits masked, the TIC stellar density),
then saves each pass's periodogram and best signal for figure2_plot.py.

Usage, from the repository root::

    python scripts/g249_11/figure2_compute.py

Writes ``results/g249-11/figure2_passes.json`` (the best signal of each pass) and
``results/g249-11/figure2_passes.npz`` (the periodograms, 37 MB, not kept in git).
"""

import json
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np

from transit_hunter.data import fetch_lightcurve
from transit_hunter.detrend import detrend
from transit_hunter.pipeline import PipelineConfig
from transit_hunter.search import iterative_search

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parents[2] / "results" / "g249-11"
config = PipelineConfig()
search_cfg = replace(config.search, stellar_density=12.681, n_workers=4)
lc = fetch_lightcurve(417732194, sectors=[19, 59, 60])
first = detrend(lc, config.detrend)
result = iterative_search(first.flat, search_cfg, raw=lc, detrend_config=config.detrend)

arrays, summary = {}, []
for k, (pg, sig) in enumerate(zip(result.periodograms, result.signals, strict=False), start=1):
    arrays.update(
        {
            f"period{k}": pg.period,
            f"sde{k}": pg.sde,
            f"snr{k}": pg.depth_snr,
            f"eligible{k}": pg.eligible,
        }
    )
    summary.append(
        {
            "pass": k,
            "period": sig.period,
            "sde": sig.sde,
            "snr": sig.snr,
            "detected": bool(sig.detected),
        }
    )
    print(
        f"pass {k}: P {sig.period:.5f} d, SDE {sig.sde:.2f}, S/N {sig.snr:.2f}, "
        f"detected {sig.detected}"
    )
np.savez_compressed(OUT / "figure2_passes.npz", **arrays)
meta = {
    "passes": summary,
    "sde_threshold": search_cfg.sde_threshold,
    "snr_threshold": search_cfg.snr_threshold,
}
(OUT / "figure2_passes.json").write_text(json.dumps(meta, indent=1))
print("saved figure2_passes.npz and figure2_passes.json")
