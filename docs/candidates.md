---
layout: default
title: Candidate verdicts
---

# Vetting of TOI planet candidates

[← Home](index.md)

TESS Objects of Interest (TOIs) whose TFOPWG disposition is still **PC** (planet
candidate) are run through the full pipeline and the vetting tests
(`scripts/vet_toi_candidates.py`).

**Selection rule** (deterministic, applied to the TOI table at run time): disposition PC;
1 d < P < 15 d; TESS magnitude ≤ 11; catalogue depth ≥ 800 ppm; ranked by the S/N proxy
depth × 10^(−0.2 (Tmag − 10)) × √(27.4 d / P), which favours bright, deep, frequently
transiting candidates; at most one TOI per star; the first five that have SPOC 2-minute
data are used.

**How a verdict is reached** (details in [Methods](methods.md#vetting-vetpy)):
any failed test gives *likely false positive*. Warnings alone give *planet candidate (with
caveats)*. Otherwise the verdict is *planet candidate (passes all tests)*. Because these
tests use only the light curve, a clean verdict means the signal is *consistent with a
planet on the target star*. It does not exclude a blended background eclipsing binary.

<!-- BEGIN: candidates -->
> **Not yet run.** Vetting of TOI planet candidates; it requires network access to `mast.stsci.edu` (light curves, TIC) and `exoplanetarchive.ipac.caltech.edu` (reference values, TOI catalogue).
>
> Generate it with `python scripts/vet_toi_candidates.py`, then run `python scripts/update_docs.py`.
<!-- END: candidates -->

Each candidate's report folder (`results/candidates/TOI-.../`) contains the search,
fit, corner, and four-panel vetting figures that the verdict is based on.
