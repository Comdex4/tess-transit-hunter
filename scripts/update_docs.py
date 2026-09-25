#!/usr/bin/env python
"""Copy result tables and figures from results/ into README.md and docs/.

Every number shown in the README and on the documentation pages is inserted by this
script from files that the analysis scripts write; nothing is typed by hand. Blocks
are delimited by ``<!-- BEGIN: key -->`` / ``<!-- END: key -->`` markers. A result
that does not exist yet is replaced by an explicit "not yet run" notice.
"""

from __future__ import annotations

import json
import re
import shutil
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DOCS = ROOT / "docs"
FIGURES = DOCS / "assets" / "figures"

PASS_ALL = "planet candidate (passes all tests)"
#: Completeness-grid fields copied into docs/_data for the interactive maps.
GRID_KEYS = ("period_edges", "radius_edges", "recovered", "total", "fraction")

NETWORK_NOTE = (
    "requires network access to `mast.stsci.edu` (light curves, TIC) and "
    "`exoplanetarchive.ipac.caltech.edu` (reference values, TOI catalogue)"
)


def load_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.exists() else None


def median(values: Any) -> float | None:
    values = list(values)
    return statistics.median(values) if values else None


def replace_block(text: str, key: str, content: str) -> str:
    pattern = re.compile(
        rf"(<!-- BEGIN: {re.escape(key)} -->\n)(.*?)(<!-- END: {re.escape(key)} -->)", re.S
    )
    if not pattern.search(text):
        raise KeyError(f"marker {key!r} not found")
    # Blank lines around the content: kramdown (GitHub Pages) only parses a table or list
    # that follows an HTML comment when a blank line separates them.
    return pattern.sub(
        lambda m: m.group(1) + "\n" + content.strip("\n") + "\n\n" + m.group(3), text
    )


def png_image_data(path: Path) -> list[bytes]:
    """The critical chunks of a PNG file (header, pixels): its image without metadata."""
    data = path.read_bytes()
    chunks, pos = [], 8
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos : pos + 4], "big")
        if data[pos + 4 : pos + 5].isupper():  # ancillary chunk types start in lower case
            chunks.append(data[pos + 4 : pos + 8 + length])
        pos += 12 + length
    return chunks


def copy_figure(src: Path, dest: Path) -> None:
    """Copy a figure unless ``dest`` already holds the same image (metadata aside)."""
    if dest.exists() and png_image_data(src) == png_image_data(dest):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def figure(src: Path, name: str, alt: str, from_docs: bool) -> str:
    """Copy a figure into docs/assets/figures and return a Markdown image link."""
    if not src.exists():
        return ""
    copy_figure(src, FIGURES / name)
    prefix = "assets/figures" if from_docs else "docs/assets/figures"
    return f"![{alt}]({prefix}/{name})"


def not_run(what: str, command: str, extra: str = "") -> str:
    return (
        f"> **Not yet run.** {what} {extra}\n>\n"
        f"> Generate it with `{command}`, then run `python scripts/update_docs.py`.\n"
    )


# --------------------------------------------------------------------------- blocks
def status_block() -> str:
    rows = [
        (
            "False-alarm calibration (synthetic noise)",
            RESULTS / "calibration/summary.json",
            "offline",
        ),
        (
            "End-to-end benchmark on synthetic systems",
            RESULTS / "synthetic_benchmark/benchmark.json",
            "offline",
        ),
        (
            "Injection–recovery on a synthetic light curve",
            RESULTS / "injection_synthetic/completeness.json",
            "offline",
        ),
        ("Validation on confirmed TESS planets", RESULTS / "validation/validation.json", "network"),
        ("Vetting of TOI planet candidates", RESULTS / "candidates/candidates.json", "network"),
        ("Injection–recovery on a real TESS light curve", None, "network"),
    ]
    real_injection = sorted(RESULTS.glob("injection_tic*/completeness.json"))
    lines = ["| analysis | needs | status |", "|---|---|---|"]
    missing_network = 0
    for label, path, needs in rows:
        if path is None:
            done = bool(real_injection)
        else:
            done = path.exists()
        need = "offline (synthetic data)" if needs == "offline" else "MAST + Exoplanet Archive"
        if done:
            state = "done"
        elif needs == "network":
            state = "**not yet run** (needs network access)"
            missing_network += 1
        else:
            state = "**not yet run**"
        lines.append(f"| {label} | {need} | {state} |")
    lines.append("")
    if missing_network:
        lines.append(
            "The analyses still to run use the TESS archives: `mast.stsci.edu` (TESS light "
            "curves, TIC) and `exoplanetarchive.ipac.caltech.edu` (reference values, TOI "
            "catalogue). Their code is tested offline against synthetic data and mocked "
            "archive responses. "
        )
    else:
        lines.append(
            "The analyses of real TESS data used every SPOC 2-minute sector available from "
            "MAST and reference values from the NASA Exoplanet Archive at the time they were "
            "run. "
        )
    lines[-1] += (
        "The result tables, figures, and summary numbers on these pages are copied from "
        "`results/` by `scripts/update_docs.py`, not typed by hand."
    )
    return "\n".join(lines)


def calibration_block(from_docs: bool) -> str:
    table = RESULTS / "calibration/false_alarms.md"
    if not table.exists():
        return not_run("False-alarm calibration.", "python scripts/calibrate_false_alarms.py")
    fig = figure(
        RESULTS / "calibration/false_alarms.png",
        "false_alarms.png",
        "SDE and S/N of the strongest BLS peak in noise-only light curves",
        from_docs,
    )
    return table.read_text() + "\n" + fig + "\n"


def benchmark_block(from_docs: bool) -> str:
    table = RESULTS / "synthetic_benchmark/benchmark.md"
    if not table.exists():
        return not_run(
            "Synthetic end-to-end benchmark.", "python scripts/run_synthetic_benchmark.py"
        )
    fig = figure(
        RESULTS / "synthetic_benchmark/benchmark_errors.png",
        "benchmark_errors.png",
        "Recovered minus true period, depth and radius for the synthetic systems",
        from_docs,
    )
    return table.read_text() + "\n" + fig + "\n"


def completeness_block(folder: Path, from_docs: bool, label: str, with_table: bool = True) -> str:
    summary = load_json(folder / "completeness.json")
    if summary is None:
        return ""
    base = summary["base_lightcurve"]
    cdpp = base.get("cdpp_ppm", {})
    name = f"completeness_{folder.name}.png"
    fig = figure(folder / "completeness.png", name, f"Completeness map ({label})", from_docs)
    description = (
        f"{summary['n_injections']} injections ({summary['radius_edges'][0]:.3g}–"
        f"{summary['radius_edges'][-1]:.3g} R⊕, {summary['period_edges'][0]:.3g}–"
        f"{summary['period_edges'][-1]:.3g} d) into {label}: {base.get('n_points')} points over "
        f"{base.get('baseline_days', 0):.1f} days; robust scatter of the flattened light curve "
        + ", ".join(f"{k}: {v:.0f} ppm" for k, v in cdpp.items())
        + f". Overall recovery: {100 * summary['overall_fraction']:.1f} %; "
        f"{summary.get('n_aliases', 0)} injections were found only at an alias period."
    )
    if not with_table:
        return f"{description}\n\n{fig}\n"
    table = (folder / "completeness.md").read_text()
    return f"{description}\n\n{fig}\n\n{table}"


def performance_block() -> str:
    table = RESULTS / "performance/search_scaling.md"
    if not table.exists():
        return not_run("Search-cost benchmark.", "python scripts/benchmark_search_scaling.py")
    return table.read_text()


def validation_block(from_docs: bool) -> str:
    table = RESULTS / "validation/validation.md"
    if not table.exists():
        return not_run(
            "Validation on confirmed TESS planets; it",
            "python scripts/validate_known_planets.py",
            NETWORK_NOTE + ".",
        )
    fig = figure(
        RESULTS / "validation/validation_errors.png",
        "validation_errors.png",
        "Recovered minus published values for confirmed planets",
        from_docs,
    )
    return table.read_text() + "\n" + fig + "\n"


def candidates_block() -> str:
    table = RESULTS / "candidates/candidates.md"
    if not table.exists():
        return not_run(
            "Vetting of TOI planet candidates; it",
            "python scripts/vet_toi_candidates.py",
            NETWORK_NOTE + ".",
        )
    return table.read_text()


def real_lightcurve_label(base: dict[str, Any]) -> str:
    """Short description of a real base light curve, e.g. 'TIC 1, sectors 1, 2'."""
    label = str(base.get("source", "real light curve"))
    sectors = base.get("sectors") or []
    if sectors:
        label += f", sector{'s' if len(sectors) > 1 else ''} " + ", ".join(map(str, sectors))
    if base.get("masked_ephemerides"):
        label += ", known planets masked"
    return label


def real_completeness_block(from_docs: bool) -> str:
    folders = sorted(p.parent for p in RESULTS.glob("injection_tic*/completeness.json"))
    if not folders:
        return not_run(
            "Injection–recovery on a real TESS light curve; it",
            "python scripts/run_injection_recovery.py --tic <TIC> --mask-known "
            "--out results/injection_tic<TIC>",
            NETWORK_NOTE + ".",
        )
    blocks = []
    for folder in folders:
        base = json.loads((folder / "completeness.json").read_text())["base_lightcurve"]
        label = f"the SPOC 2-minute light curve of {real_lightcurve_label(base)}"
        blocks.append(completeness_block(folder, from_docs, label))
    return "\n\n".join(blocks)


def synthetic_completeness_block(from_docs: bool, with_table: bool = True) -> str:
    folder = RESULTS / "injection_synthetic"
    text = completeness_block(
        folder, from_docs, "a synthetic TESS-like light curve of a G dwarf", with_table
    )
    return text or not_run(
        "Synthetic injection–recovery.",
        "python scripts/run_injection_recovery.py --synthetic --out results/injection_synthetic",
    )


# --------------------------------------------------------------------------- site data
#: Report figures shown on the site's pipeline pages, by report folder (relative to
#: results/). Each is copied to docs/assets/examples/<folder name>/.
EXAMPLE_FIGURES = {
    "synthetic_benchmark/SYN-3": [
        "detrending.png",
        "search_summary.png",
        "periodogram_1.png",
        "fit_1.png",
        "corner_1.png",
        "vetting_1.png",
    ],
    "synthetic_benchmark/SYN-5": ["vetting_1.png", "fold_1.png"],
    "validation/WASP-18": ["vetting_1.png"],
    "validation/TOI-270": ["search_summary.png"],
    "validation/L_98-59": ["vetting_4.png"],
}


def site_data() -> None:
    """Write docs/_data/*.json: headline numbers and the completeness grid for the site.

    Jekyll exposes these files as ``site.data.stats`` and ``site.data.completeness``; the
    home page's stat cards and the interactive completeness map read them.
    """
    data_dir = DOCS / "_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {}

    bench = load_json(RESULTS / "synthetic_benchmark/benchmark.json")
    if bench:
        comp = bench["comparison"]
        (data_dir / "benchmark.json").write_text(json.dumps(comp, indent=1) + "\n")
        found = [c for c in comp if c.get("recovered")]
        stats["benchmark"] = {
            "n_planets": len(comp),
            "n_recovered": len(found),
            "n_systems": sum(not s.get("eclipsing_binary") for s in bench["systems"]),
            "max_period_err_pct": max(abs(c["period_pct"]) for c in found),
            "max_radius_err_pct": max(abs(c["rp_pct"]) for c in found),
            "median_radius_err_pct": sorted(abs(c["rp_pct"]) for c in found)[len(found) // 2],
            "eb_rejected": all(
                any("false positive" in v for v in s["verdicts"])
                for s in bench["systems"]
                if s.get("eclipsing_binary")
            ),
        }

    comp_json = load_json(RESULTS / "injection_synthetic/completeness.json")
    if comp_json:
        grid = {k: comp_json[k] for k in GRID_KEYS}
        grid["label"] = "synthetic G dwarf, 2 sectors"
        (data_dir / "completeness.json").write_text(json.dumps(grid, indent=1) + "\n")
        stats["completeness"] = {
            "n_injections": comp_json["n_injections"],
            "overall_pct": 100 * comp_json["overall_fraction"],
        }

    cal = load_json(RESULTS / "calibration/summary.json")
    if cal:
        single = [c for c in cal["cases"] if c["n_sectors"] == 1]
        stats["calibration"] = {
            "single_sector_false_alarms": sum(c["n_false_alarms"] for c in single),
            "single_sector_trials": cal["n_per_case"] * len(single),
            "n_light_curves": cal["n_per_case"] * len(cal["cases"]),
        }

    val = load_json(RESULTS / "validation/validation.json")
    if val:
        comp = val["comparison"]
        found = [c for c in comp if c.get("recovered")]
        unmatched = [
            d
            for h in val["hosts"]
            for d in h.get("detections", [])
            if d["role"] == "candidate" and not d["matches"]
        ]
        stats["validation"] = {
            "n_hosts": len(val["hosts"]),
            "n_planets": len(comp),
            "n_recovered": len(found),
            "max_period_err_pct": max((abs(c["period_pct"]) for c in found), default=None),
            "median_rp_rs_err_pct": median(
                abs(c["rp_rs_pct"]) for c in found if c.get("rp_rs_pct") is not None
            ),
            "n_pass_all": sum(c.get("verdict") == PASS_ALL for c in found),
            "n_false_positive": sum("false positive" in (c.get("verdict") or "") for c in found),
            "n_unmatched_detections": len(unmatched),
        }

    cand = load_json(RESULTS / "candidates/candidates.json")
    if cand:
        verdicts = [e["verdict"] for e in cand["candidates"]]
        stats["candidates"] = {
            "n_tois": len(verdicts),
            "n_recovered": sum(e["recovered"] for e in cand["candidates"]),
            "n_pass_all": sum(v == PASS_ALL for v in verdicts),
            "n_caveats": sum("with caveats" in v for v in verdicts),
            "n_false_positive": sum("false positive" in v for v in verdicts),
        }

    real = sorted(RESULTS.glob("injection_tic*/completeness.json"))
    if real:
        comp_json = json.loads(real[0].read_text())
        base = comp_json["base_lightcurve"]
        grid = {k: comp_json[k] for k in GRID_KEYS}
        grid["label"] = real_lightcurve_label(base)
        (data_dir / "completeness_real.json").write_text(json.dumps(grid, indent=1) + "\n")
        stats["completeness_real"] = {
            "source": base.get("source"),
            "n_sectors": len(base.get("sectors", [])),
            "n_injections": comp_json["n_injections"],
            "overall_pct": 100 * comp_json["overall_fraction"],
        }

    perf = load_json(RESULTS / "performance/search_scaling.json")
    if perf:
        rows = perf["rows"]
        (data_dir / "search_scaling.json").write_text(json.dumps(perf, indent=1) + "\n")
        stats["performance"] = {
            "one_sector_s": rows[0]["seconds_per_iteration"],
            "longest_case": rows[-2]["case"],
            "longest_s": rows[-2]["seconds_per_iteration"],
        }

    (data_dir / "stats.json").write_text(json.dumps(stats, indent=1) + "\n")

    # Example pipeline figures shown on the pipeline pages of the site.
    examples = DOCS / "assets" / "examples"
    for folder, names in EXAMPLE_FIGURES.items():
        for name in names:
            src = RESULTS / folder / name
            if src.exists():
                copy_figure(src, examples / Path(folder).name / name)
    print(f"updated {(data_dir / 'stats.json').relative_to(ROOT)}")


def main() -> None:
    targets = {
        ROOT / "README.md": False,
        DOCS / "index.md": True,
        DOCS / "validation.md": True,
        DOCS / "completeness.md": True,
        DOCS / "candidates.md": True,
    }
    builders = {
        "status": lambda d: status_block(),
        "calibration": calibration_block,
        "benchmark": benchmark_block,
        "validation": validation_block,
        "candidates": lambda d: candidates_block(),
        "performance": lambda d: performance_block(),
        "completeness_synthetic": synthetic_completeness_block,
        "completeness_summary": lambda d: synthetic_completeness_block(d, with_table=False),
        "completeness_real": real_completeness_block,
    }
    for path, from_docs in targets.items():
        if not path.exists():
            continue
        text = path.read_text()
        for key, build in builders.items():
            if f"<!-- BEGIN: {key} -->" in text:
                text = replace_block(text, key, build(from_docs))
        path.write_text(text)
        print(f"updated {path.relative_to(ROOT)}")
    site_data()


if __name__ == "__main__":
    main()
