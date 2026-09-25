# tess-transit-hunter

[![CI](https://github.com/comdex4/tess-transit-hunter/actions/workflows/ci.yml/badge.svg)](https://github.com/comdex4/tess-transit-hunter/actions/workflows/ci.yml)

A Python research pipeline that **finds, fits, and vets transiting exoplanets in NASA TESS
2-minute light curves**. For one TIC target it:

1. downloads every SPOC 2-minute PDCSAP sector, removes flagged and NaN cadences, clips
   upward outliers, and caches the result (`data.py`);
2. removes stellar variability with a robust windowed biweight filter, masking known
   transits when requested (`detrend.py`);
3. runs an **iterative Box Least Squares search** over a physically bounded period ×
   duration grid, with red-noise-aware S/N, SDE, and trial-corrected thresholds
   (`search.py`);
4. fits each detection with a **batman** transit model sampled by **emcee**, reports
   posterior medians and 68 % intervals, and derives the planet radius from the TIC stellar
   radius (`fit.py`);
5. applies **vetting tests** for eclipsing binaries: odd/even depths, a secondary eclipse at
   phase 0.5 (and at any phase), V- versus U-shape, transit-implied versus catalogue stellar
   density, and radius; candidates at the star's rotation period get a warning (`vet.py`);
6. measures **completeness** by injection–recovery over a period × radius grid, in
   parallel (`inject.py`).

Full write-up (methods, validation, completeness, candidate verdicts, limitations):
**<https://comdex4.github.io/tess-transit-hunter/>** (source in [`docs/`](docs/)).

## Status of the results

<!-- BEGIN: status -->
| analysis | needs | status |
|---|---|---|
| False-alarm calibration (synthetic noise) | offline (synthetic data) | done |
| End-to-end benchmark on synthetic systems | offline (synthetic data) | done |
| Injection–recovery on a synthetic light curve | offline (synthetic data) | done |
| Validation on confirmed TESS planets | MAST + Exoplanet Archive | **not yet run** (needs network access) |
| Vetting of TOI planet candidates | MAST + Exoplanet Archive | **not yet run** (needs network access) |
| Injection–recovery on a real TESS light curve | MAST + Exoplanet Archive | **not yet run** (needs network access) |

The analyses that need the TESS archives could not be run where this repository was built: that environment's network policy blocked `mast.stsci.edu` (TESS light curves, TIC) and `exoplanetarchive.ipac.caltech.edu` (reference values, TOI catalogue). Their code is complete and tested offline against synthetic data and mocked archive responses. The result tables, figures, and summary numbers on these pages are copied from `results/` by `scripts/update_docs.py`, not typed by hand.
<!-- END: status -->

## Installation

Python ≥ 3.11.

```bash
git clone https://github.com/comdex4/tess-transit-hunter.git
cd tess-transit-hunter
pip install -e ".[dev]"          # add ,notebook for the Jupyter notebook
```

Dependencies: numpy, scipy, astropy (BoxLeastSquares), astroquery (NASA Exoplanet Archive,
TIC), lightkurve, batman-package, emcee, corner, matplotlib, and wotan (biweight
detrending).

## Usage

### Command line

```bash
# Full pipeline for one star: all 2-min sectors, search, MCMC fits, vetting, report folder
transit-hunter run --tic 261136679 --outdir reports/

# Useful options
transit-hunter run --tic 261136679 --sectors 1 4 13 --window 1.0 --max-period 30 \
    --max-signals 3 --quick --workers 8

# Download, clean, and cache only
transit-hunter fetch --tic 261136679

# Offline demo on a synthetic three-planet M-dwarf system
transit-hunter demo --outdir reports/
```

Each run writes `reports/TIC<ID>/` containing:

| file | contents |
|---|---|
| `report.json` | every number: target, stellar parameters, noise, all search iterations, posterior summaries, derived quantities, vetting tests, configuration, software versions, data provenance |
| `summary.md` | human-readable summary with the vetting reasoning |
| `detrending.png` | raw flux with trend, flattened flux (one row per observing season) |
| `search_summary.png`, `periodogram_<n>.png`, `fold_<n>.png` | BLS periodograms and phase-folded light curves per iteration |
| `fit_<n>.png`, `corner_<n>.png` | best-fitting model with residuals; posterior corner plot |
| `vetting_<n>.png` | odd/even, phase 0.5, transit shape, stellar density |

An example report folder, from the synthetic benchmark (three planets around an M dwarf), is
in [`results/synthetic_benchmark/SYN-3/`](results/synthetic_benchmark/SYN-3/).

Downloads need network access to `mast.stsci.edu`. Stellar parameters come from the TIC via
MAST, falling back to the values in the FITS header. Processed light curves are cached in
`~/.cache/transit_hunter` (override with `TRANSIT_HUNTER_CACHE` or `--cache-dir`).

### Python

```python
from transit_hunter.data import fetch_lightcurve
from transit_hunter.catalog import get_stellar_params
from transit_hunter.pipeline import PipelineConfig, run_on_lightcurve

lc = fetch_lightcurve(261136679)                       # cleaned, stitched, cached
star = get_stellar_params(261136679, lc.meta["stellar_header"])
report = run_on_lightcurve(lc, "reports/pi_Men", star, PipelineConfig(), name="pi Men")
```

The pieces can also be used on their own: `detrend.detrend`,
`search.iterative_search`, `fit.fit_transit`, `vet.run_vetting`, and
`inject.run_injections`.

### Analyses

| script | what it produces | needs network |
|---|---|---|
| `scripts/validate_known_planets.py` | recovered vs published P, depth, Rp for confirmed planets (plus [notebook](notebooks/validation_known_planets.ipynb)) | yes |
| `scripts/vet_toi_candidates.py` | pipeline + vetting verdicts for 3–5 PC TOIs with 2-min data | yes |
| `scripts/run_injection_recovery.py --tic <ID> --mask-known` | completeness map for a real light curve (its known planets masked) | yes |
| `scripts/run_injection_recovery.py --synthetic` | completeness map for a synthetic light curve | no |
| `scripts/run_synthetic_benchmark.py` | end-to-end test on synthetic systems with known truth | no |
| `scripts/calibrate_false_alarms.py` | false-alarm rate on noise-only light curves | no |
| `scripts/benchmark_search_scaling.py` | search cost versus amount of data | no |
| `scripts/update_docs.py` | copies result tables and figures into this README and `docs/` | no |

## Results

Every number below is copied from `results/` by `scripts/update_docs.py`. None is typed by
hand.

### End-to-end benchmark on synthetic systems (truth known)

Simulated TESS-like light curves go through the full pipeline (detrend, iterative BLS,
MCMC, vetting). They cover a hot Jupiter, a small planet around a bright star observed for
six sectors, a three-planet M-dwarf system, and a long-period planet, plus an eclipsing
binary as a negative control. These are **simulations, not TESS data**; the "published"
columns hold the injected (true) values.

<!-- BEGIN: benchmark -->
| planet | P published (d) | P recovered (d) | ΔP | depth published (ppm) | depth recovered (ppm) | Δdepth | Rp published (R⊕) | Rp recovered (R⊕) | ΔRp |
|---|---|---|---|---|---|---|---|---|---|
| SYN-1 b | 0.940000 | 0.940000 ± 8.8e-07 | -0.0000% | 9091 | 9074 ± 36 | -0.2% | 13.00 | 12.98 ± 0.39 | -0.1% |
| SYN-2 b | 6.270000 | 6.270082 ± 5e-05 | +0.0013% | 278 | 268 ± 23 | -3.7% | 2.00 | 1.98 ± 0.1 | -1.2% |
| SYN-3 b | 3.360000 | 3.359982 ± 6.5e-05 | -0.0005% | 984 | 1148 ± 85 | +16.7% | 1.30 | 1.40 ± 0.067 | +8.0% |
| SYN-3 c | 5.660000 | 5.660025 ± 4.9e-05 | +0.0004% | 3353 | 3313 ± 1.1e+02 | -1.2% | 2.40 | 2.39 ± 0.082 | -0.4% |
| SYN-3 d | 11.380000 | 11.379804 ± 0.00022 | -0.0017% | 2567 | 2771 ± 2.7e+02 | +8.0% | 2.10 | 2.19 ± 0.12 | +4.1% |
| SYN-4 b | 35.600000 | 35.599620 ± 0.00021 | -0.0011% | 1345 | 1409 ± 62 | +4.8% | 2.80 | 2.87 ± 0.11 | +2.4% |

Depth is the geometric depth (Rp/R*)² unless noted; Δ = 100 × (recovered − published) / published.


| system | description | sectors | detections | vetting verdicts |
|---|---|---|---|---|
| SYN-1 | hot Jupiter on a sub-day orbit around an F star | 2 | 1 | planet candidate (passes all tests) |
| SYN-2 | small planet around a bright, quiet G dwarf observed for six sectors | 6 | 1 | planet candidate (passes all tests) |
| SYN-3 | compact three-planet system around an M dwarf | 3 | 3 | planet candidate (passes all tests); planet candidate (passes all tests); planet candidate (passes all tests) |
| SYN-4 | long-period sub-Neptune around a K dwarf (six contiguous sectors) | 6 | 1 | planet candidate (passes all tests) |
| SYN-5 | eclipsing binary found at half its period (negative control) | 2 | 1 | likely false positive |

![Recovered minus true period, depth and radius for the synthetic systems](docs/assets/figures/benchmark_errors.png)
<!-- END: benchmark -->

### Completeness (injection–recovery)

<!-- BEGIN: completeness_summary -->
2048 injections (0.7–8 R⊕, 0.5–20 d) into a synthetic TESS-like light curve of a G dwarf: 38020 points over 54.8 days; robust scatter of the flattened light curve 0.5h: 185 ppm, 1h: 140 ppm, 2h: 99 ppm. Overall recovery: 71.7 %; 0 injections were found only at an alias period.

![Completeness map (a synthetic TESS-like light curve of a G dwarf)](docs/assets/figures/completeness_injection_synthetic.png)
<!-- END: completeness_summary -->

The per-cell table and the real-light-curve version are on the
[completeness page](https://comdex4.github.io/tess-transit-hunter/completeness.html).

### Confirmed TESS planets

<!-- BEGIN: validation -->
> **Not yet run.** Validation on confirmed TESS planets; it requires network access to `mast.stsci.edu` (light curves, TIC) and `exoplanetarchive.ipac.caltech.edu` (reference values, TOI catalogue).
>
> Generate it with `python scripts/validate_known_planets.py`, then run `python scripts/update_docs.py`.
<!-- END: validation -->

### TOI planet candidates

<!-- BEGIN: candidates -->
> **Not yet run.** Vetting of TOI planet candidates; it requires network access to `mast.stsci.edu` (light curves, TIC) and `exoplanetarchive.ipac.caltech.edu` (reference values, TOI catalogue).
>
> Generate it with `python scripts/vet_toi_candidates.py`, then run `python scripts/update_docs.py`.
<!-- END: candidates -->

### False-alarm calibration

<!-- BEGIN: calibration -->
Noise-only synthetic light curves (no transits), 150 per case, searched without a stellar-density prior (the widest duration grid). A false alarm is a strongest peak with SDE ≥ 7, S/N at or above the applied threshold (the larger of 7 and the trial-corrected 1 % level), and at least two transits. In brackets: false alarms that the vetting would flag as lying at the star's rotation period, half of it, or twice it (Lomb–Scargle of the un-detrended light curve). The last column counts light curves in which at least one stronger peak was skipped as stellar variability before the strongest peak was chosen.

| noise regime | sectors | median 1-h CDPP (ppm) | SDE median / 99th pct / max | S/N median / 99th pct / max | S/N threshold applied | false alarms (at P_rot) | peaks skipped as variability |
|---|---|---|---|---|---|---|---|
| quiet | 1 | 59 | 4.9 / 6.6 / 8.1 | 5.3 / 7.0 / 7.3 | 7.00 | 1/150 (0) | 20/150 |
| moderate | 1 | 173 | 4.3 / 6.3 / 6.7 | 4.9 / 9.1 / 11.6 | 7.00 | 0/150 (0) | 22/150 |
| active | 1 | 873 | 2.8 / 5.2 / 5.5 | 5.1 / 19.1 / 21.8 | 7.00 | 0/150 (0) | 91/150 |
| moderate | 3 | 170 | 5.0 / 8.0 / 8.6 | 6.1 / 11.5 / 13.8 | 7.00 | 11/150 (10) | 95/150 |

![SDE and S/N of the strongest BLS peak in noise-only light curves](docs/assets/figures/false_alarms.png)
<!-- END: calibration -->

## Tests and CI

```bash
pytest          # synthetic data only, no network; a few minutes
ruff check src tests scripts && ruff format --check src tests scripts
```

The tests cover data cleaning and caching (with a faked lightkurve), detrending, BLS
recovery of injected signals (including near-resonant pairs and noise-only light curves),
fit accuracy on noiseless models, each vetting test on synthetic planets and eclipsing
binaries, injection–recovery bookkeeping, archive-table parsing, and the CLI end to end.
GitHub Actions runs ruff and pytest on Python 3.11 and 3.12 for every push and pull request
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Documentation site

The write-up in [`docs/`](docs/) is a Jekyll site for GitHub Pages. To publish it, go to
**Settings → Pages → Build and deployment**, choose *Deploy from a branch*, and select the
default branch and the `/docs` folder.

## Repository layout

```
src/transit_hunter/   data, detrend, search, fit, vet, inject, catalog, validation,
                      pipeline, cli, synthetic (simulator), models, plotting, utils
scripts/              analyses listed above
notebooks/            validation notebook
tests/                offline pytest suite
results/              outputs of the analysis scripts (JSON / Markdown / figures)
docs/                 GitHub Pages write-up
```

## Limitations

In short: the vetting cannot exclude blended background binaries (no pixel-level analysis),
orbits are assumed circular, and synthetic completeness is optimistic because simulated
light curves lack real instrumental systematics. For spotted stars observed over several
sectors, residual spot modulation produces false alarms at the rotation period and half of
it; the vetting flags candidates there but cannot tell them apart from planets. Results
that need the TESS archives are marked "not yet run" until the scripts have been run with
network access. Details: [docs/limitations.md](docs/limitations.md).

## License

MIT, see [LICENSE](LICENSE).
