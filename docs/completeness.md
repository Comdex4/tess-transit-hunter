---
layout: default
title: Completeness
---

# Completeness from injection–recovery

[← Home](index.md)

Synthetic transits are multiplied into a light curve **before detrending**, and the full
detrend + iterative BLS search is run exactly as for a real target
(`scripts/run_injection_recovery.py`; method in [Methods](methods.md#injectionrecovery-injectpy)).
An injection counts as recovered only if a **detected** signal matches its period to
within 1 % and a mid-transit time falls within half a transit duration of an injected
transit. Detections at 1/2, 2, 1/3, or 3 times the period are recorded separately as aliases
and are not counted as recoveries. Tables list the percentage recovered, with the number
recovered / injected in brackets. The table is the exact numerical twin of the figure.

## Synthetic TESS-like light curve

A simulated two-sector light curve of a Sun-like star with white noise, correlated noise,
and rotational modulation. It has no instrumental systematics, so this map is an **upper
limit** on real-data completeness at the same noise level.

<!-- BEGIN: completeness_synthetic -->
2048 injections (0.7–8 R⊕, 0.5–20 d) into a synthetic TESS-like light curve of a G dwarf: 38020 points over 54.8 days; robust scatter of the flattened light curve 0.5h: 185 ppm, 1h: 140 ppm, 2h: 99 ppm. Overall recovery: 71.7 %; 0 injections were found only at an alias period.

![Completeness map (a synthetic TESS-like light curve of a G dwarf)](assets/figures/completeness_injection_synthetic.png)

| R_p (R⊕) \ P (d) | 0.5–0.793 | 0.793–1.26 | 1.26–1.99 | 1.99–3.16 | 3.16–5.01 | 5.01–7.95 | 7.95–12.6 | 12.6–20 |
|---|---|---|---|---|---|---|---|---|
| 5.9–8 | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) |
| 4.35–5.9 | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) |
| 3.21–4.35 | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) |
| 2.37–3.21 | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 97% (31/32) |
| 1.75–2.37 | 100% (32/32) | 100% (32/32) | 100% (32/32) | 100% (32/32) | 97% (31/32) | 94% (30/32) | 91% (29/32) | 50% (16/32) |
| 1.29–1.75 | 100% (32/32) | 94% (30/32) | 94% (30/32) | 75% (24/32) | 50% (16/32) | 28% (9/32) | 3% (1/32) | 6% (2/32) |
| 0.949–1.29 | 72% (23/32) | 66% (21/32) | 38% (12/32) | 22% (7/32) | 3% (1/32) | 0% (0/32) | 0% (0/32) | 0% (0/32) |
| 0.7–0.949 | 6% (2/32) | 6% (2/32) | 0% (0/32) | 0% (0/32) | 0% (0/32) | 0% (0/32) | 0% (0/32) | 0% (0/32) |
<!-- END: completeness_synthetic -->

## Real TESS light curve

<!-- BEGIN: completeness_real -->
> **Not yet run.** Injection–recovery on a real TESS light curve; it requires network access to `mast.stsci.edu` (light curves, TIC) and `exoplanetarchive.ipac.caltech.edu` (reference values, TOI catalogue).
>
> Generate it with `python scripts/run_injection_recovery.py --tic <TIC> --mask-known --out results/injection_tic<TIC>`, then run `python scripts/update_docs.py`.
<!-- END: completeness_real -->

### Interpreting the maps

* Completeness falls with radius because depth scales as (Rp/R*)². It falls with period
  because fewer transits are observed, and the S/N grows only as the square root of their
  number. In light curves with long gaps, some long-period injections also have fewer
  than the two transits a detection requires (`n_transits_in_data` in `injections.csv`).
* The limiting S/N is set by the detection criteria (SDE ≥ 7, red-noise S/N ≥ max(7,
  trial-corrected level)), not by the injection grid.
* The per-injection results, including the found period, S/N, SDE, and the number of
  injected transits that fell in the data, are in `injections.csv` in each results folder.
