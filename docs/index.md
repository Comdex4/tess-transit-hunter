---
layout: default
title: tess-transit-hunter
---

# tess-transit-hunter

A Python pipeline that finds transiting planets in NASA **TESS** 2-minute light curves,
fits them, and checks them for the signatures of eclipsing binaries.

For one TIC target, **`transit-hunter run --tic <ID>`** downloads every SPOC 2-minute sector,
cleans and detrends the photometry, runs an iterative Box Least Squares search, fits each
detection with a `batman` transit model sampled by `emcee`, applies six vetting tests, and
writes a report folder of figures plus a JSON summary.

| page | contents |
|---|---|
| [Methods](methods.md) | every processing step, with the reasoning behind the defaults |
| [Validation](validation.md) | recovery of confirmed TESS planets; false-alarm calibration; end-to-end synthetic test |
| [Completeness](completeness.md) | injection–recovery tests over a period × radius grid |
| [Candidate verdicts](candidates.md) | vetting of TESS Objects of Interest that are still planet candidates |
| [Limitations](limitations.md) | what the pipeline does not do, and where its numbers should not be trusted |

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

## Reproducing everything

```bash
pip install -e ".[dev]"
pytest                                               # offline test suite (synthetic data)

# offline analyses (synthetic data)
python scripts/calibrate_false_alarms.py             # noise-only false-alarm calibration
python scripts/benchmark_search_scaling.py           # search cost vs amount of data
python scripts/run_synthetic_benchmark.py            # end-to-end test with known truth
python scripts/run_injection_recovery.py --synthetic --out results/injection_synthetic

# analyses of real TESS data (need MAST + NASA Exoplanet Archive access)
python scripts/validate_known_planets.py
python scripts/vet_toi_candidates.py
python scripts/run_injection_recovery.py --tic <TIC> --mask-known --out results/injection_tic<TIC>

python scripts/update_docs.py                        # copy the new numbers into these pages
```

Source code: [github.com/comdex4/tess-transit-hunter](https://github.com/comdex4/tess-transit-hunter)
