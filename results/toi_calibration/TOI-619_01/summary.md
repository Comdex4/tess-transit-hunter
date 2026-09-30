# TOI-619.01

* Sectors: 34, 35; 30527 points over 50.9 days
* Host star (TIC v8 (MAST catalogs)): R* = n/a R☉, Teff = n/a K, ρ* = n/a ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 337 ppm, 1h: 256 ppm, 2h: 207 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 8.78 d, semi-amplitude 187 ppm, power 0.11

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 1.80843 | 2252.2298 | 2.44 | 861 | 25.1 | 11.0 | detected |
| 2 | 0.78489 | 2251.5125 | 2.91 | 106 | 5.2 | 3.9 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.8080881 +0.00018 / −0.00019 |
| T0 (BTJD) | 2252.23204 +0.0016 / −0.0017 |
| Rp/R* | 0.147 +0.35 / −0.098 |
| a/R* | 1.66 +0.54 / −0.15 |
| b | 1.09 +0.36 / −0.15 |
| T14 (h) | 4.59 +0.25 / −0.31 |
| depth k² (ppm) | 2.16e+04 +2.3e+05 / −1.9e+04 |
| ρ* (ρ☉) | 0.0187 +0.025 / −0.0046 |
| Rp (R⊕) | – |

MCMC: 20000 steps, 9 times the longest autocorrelation time (2313 steps); 1560 samples after burn-in and thinning, acceptance 0.13; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 1121±75 ppm vs even 1088±78 ppm: 0.3σ difference (uncertainties include the 271 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (6±28 ppm, 0.2σ)
* [warn] shape: intermediate: ingress+egress = 0.75 of the duration; posterior P(grazing) = 0.83
* [n/a] density: no fitted or catalogue density
* [n/a] radius: no stellar radius
* [pass] coverage: 22 of 25 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (8.78 d) or its multiples
* [fail] centroid: the dip is 11.2″ from the target (3.6σ, 2 sectors), at TIC 767411107 (Tmag 16.2, 8″ from the target), which is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
