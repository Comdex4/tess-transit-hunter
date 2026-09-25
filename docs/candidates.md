---
layout: default
title: "Candidate verdicts"
kicker: "Results"
lede: "TESS Objects of Interest that are still planet candidates, run through the full pipeline and its vetting tests."
---



TESS Objects of Interest (TOIs) whose TFOPWG disposition is still **PC** (planet
candidate) are run through the full pipeline and the vetting tests
(`scripts/vet_toi_candidates.py`).

**Selection rule** (deterministic, applied to the TOI table at run time): disposition PC;
1 d < P < 15 d; TESS magnitude ≤ 11; catalogue depth ≥ 800 ppm; ranked by the S/N proxy
depth × 10^(−0.2 (Tmag − 10)) × √(27.4 d / P), which favours bright, deep, frequently
transiting candidates; at most one TOI per star; the first five with SPOC 2-minute light
curves filed under their own TIC ID are used. The TOI table was queried on 25 September 2026.

**Tests that cannot run** (for example the density and radius tests when the TIC has no
stellar radius) are marked n/a and do not count against a candidate, so check the list
below before reading much into a clean verdict.

**How a verdict is reached** (details in [Methods](methods.md#vetting-vetpy)):
any failed test gives *likely false positive*. Warnings alone give *planet candidate (with
caveats)*. Otherwise the verdict is *planet candidate (passes all tests)*. Because these
tests use only the light curve, a clean verdict means the signal is *consistent with a
planet on the target star*. It does not exclude a blended background eclipsing binary.

<!-- BEGIN: candidates -->

| TOI | TIC | catalogue P (d) | recovered P (d) | Rp (R⊕) | verdict |
|---|---|---|---|---|---|
| TOI-1059.01 | 380783252 | 9.44965 | 9.44966 | 48.95 | likely false positive |
| TOI-4543.01 | 435336785 | 5.77403 | 5.77459 | – | planet candidate (passes all tests) |
| TOI-4597.01 | 68573534 | 4.66638 | 4.66716 | 13.14 | planet candidate (with caveats) |
| TOI-1019.01 | 341420329 | 5.23410 | 5.23409 | 24.36 | likely false positive |
| TOI-1717.01 | 149833117 | 4.05239 | 4.05239 | 14.07 | planet candidate (passes all tests) |

### TOI-1059.01

* [pass] odd_even: odd depth 24760±172 ppm vs even 24322±146 ppm: 1.9σ difference
* [warn] secondary: no eclipse at phase 0.5 (89±87 ppm, 1.0σ); strongest dip at phase 0.07: 611 ppm (7.4σ)
* [warn] shape: intermediate: ingress+egress = 0.79 of the duration; posterior P(grazing) = 1.00
* [warn] density: transit-implied ρ* = 2.47 ρ☉ vs catalogue 1.05 ρ☉ (ratio 2.36, 3.1σ)
* [fail] radius: companion radius 4.36 R_Jup
* [pass] coverage: 19 of 19 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (10.24 d) or its multiples

### TOI-4543.01

* [pass] odd_even: odd depth 4276±119 ppm vs even 4486±137 ppm: 1.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-52±80 ppm, -0.6σ)
* [pass] shape: intermediate: ingress+egress = 0.52 of the duration; posterior P(grazing) = 0.00
* [n/a] density: no fitted or catalogue density
* [n/a] radius: no stellar radius
* [pass] coverage: 7 of 8 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

### TOI-4597.01

* [pass] odd_even: odd depth 7624±267 ppm vs even 7568±299 ppm: 0.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (2±192 ppm, 0.0σ)
* [pass] shape: U-shaped: ingress+egress = 0.19 of the duration; posterior P(grazing) = 0.00
* [warn] density: transit-implied ρ* = 1.52 ρ☉ vs catalogue 0.47 ρ☉ (ratio 3.24, 4.7σ)
* [pass] radius: companion radius 1.17 R_Jup
* [pass] coverage: 9 of 9 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

### TOI-1019.01

* [fail] odd_even: odd depth 20550±44 ppm vs even 20782±46 ppm: 3.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (23±31 ppm, 0.7σ)
* [pass] shape: U-shaped: ingress+egress = 0.45 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.45 ρ☉ vs catalogue 0.47 ρ☉ (ratio 0.97, 0.2σ)
* [pass] radius: companion radius 2.17 R_Jup
* [pass] coverage: 39 of 41 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

### TOI-1717.01

* [pass] odd_even: odd depth 8597±273 ppm vs even 8675±314 ppm: 0.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-115±215 ppm, -0.5σ)
* [pass] shape: U-shaped: ingress+egress = 0.46 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.52 ρ☉ vs catalogue 0.55 ρ☉ (ratio 0.95, 0.2σ)
* [pass] radius: companion radius 1.25 R_Jup
* [pass] coverage: 21 of 21 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (0.30 d) or its multiples

<!-- END: candidates -->

Each candidate's report folder (`results/candidates/TOI-.../`) contains the search,
fit, corner, and four-panel vetting figures that the verdict is based on.

## What the verdicts rest on

The selection favours deep, frequent transits on bright stars, and all five candidates are
0.5–2.5 % deep in the TOI catalogue: the range of giant planets, and of the eclipsing
binaries that imitate them. The pipeline recovered every one at the catalogue period.

* **TOI-1717.01 passes every test.** A companion of 1.25 R_J on a 4.05-day orbit around a
  6,578 K star, with equal odd and even depths, no secondary eclipse, a U-shaped transit
  and a transit-implied density that matches the catalogue (0.52 against 0.55 ρ☉). The star
  varies strongly at 0.30 days (1,136 ppm), far from the orbital period.
* **TOI-4543.01 passes every test that could run, but two could not.** The TIC lists no
  radius or density for this bright star (TESS magnitude 6.8), so neither the density nor
  the radius test ran, and the companion's size is unknown. The transit implies a star of
  only 0.07 ρ☉, far less dense than a dwarf, as for an evolved star. Only two sectors of
  2-minute data exist.
* **TOI-4597.01 passes with a caveat.** A 1.17 R_J companion on a 4.67-day orbit around a
  7,712 K star, with no odd/even difference and no secondary eclipse. But the transit
  implies a star 3.2 times denser than the catalogue value (4.7σ), which earns a density
  warning. An eccentric orbit can do that (see the
  [vetting page](pipeline/vet.md#stellar-density)), and so can an error in the catalogue's
  stellar radius. Two sectors.
* **TOI-1059.01 is labelled a likely false positive** by the radius test: the implied
  companion is 4.36 R_J. The dip is 2.5 % deep, and the fit puts it on a grazing orbit
  (b = 1.25, probability of grazing 1.00, which also earns a shape warning). For a grazing
  transit the size is poorly constrained: the 68 % interval of the radius ratio, 0.27–0.79,
  corresponds to about 2.4–7.3 R_J, so the lower end is just below the 2.5 R_J limit.
* **TOI-1019.01 is labelled a likely false positive** by the odd/even test alone. Its odd
  and even transits are 20,550 ± 44 and 20,782 ± 46 ppm deep (3.7σ), a difference of 1.1 %.
  Every other test passes, including the density (0.45 against 0.47 ρ☉), and the
  transit-by-transit diagnostic (`TOI-1019_01/timing_1.md`) flags none of its 39
  transits. At such a high S/N (689), a 1 % difference is significant. The pipeline cannot
  tell whether it comes from two nearly identical stars eclipsing each other or from small
  differences between transits (see [Limitations](limitations.md#vetting)). The verdict
  follows the rule, but the evidence behind it is thin.

One highly ranked TOI, TOI-651.01, was left out. Its SPOC light curves are filed under
TIC 72090499, a separate catalogue entry at the same position, not under the TOI's
TIC 72090501, and the pipeline never uses another target's light curves.

These verdicts come from the light curve alone. None of them can rule out a blended
background binary, and none replaces the TESS Follow-up Observing Program's photometry,
imaging and spectroscopy.
