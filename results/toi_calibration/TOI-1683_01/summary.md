# TOI-1683.01

* Sectors: 19; 16884 points over 25.1 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.695 R☉, Teff = 4402 K, ρ* = 2.05 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 295 ppm, 1h: 219 ppm, 2h: 170 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 11.39 d, semi-amplitude 1011 ppm, power 0.53

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 3.05770 | 1828.6415 | 1.25 | 1083 | 14.6 | 11.4 | detected |
| 2 | 6.41691 | 1829.0135 | 2.15 | 612 | 8.1 | 4.3 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.0577577 +0.00034 / −0.00028 |
| T0 (BTJD) | 1828.64177 +0.00065 / −0.00068 |
| Rp/R* | 0.0327 +0.0016 / −0.0015 |
| a/R* | 16.2 +1.8 / −3.7 |
| b | 0.45 +0.28 / −0.31 |
| T14 (h) | 1.34 +0.052 / −0.04 |
| depth k² (ppm) | 1.07e+03 +1.1e+02 / −93 |
| ρ* (ρ☉) | 6.15 +2.3 / −3.3 |
| Rp (R⊕) | 2.48 +0.25 / −0.25 |

MCMC: 20000 steps, 24 times the longest autocorrelation time (821 steps); 5120 samples after burn-in and thinning, acceptance 0.25; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1157±140 ppm vs even 1122±145 ppm: 0.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-108±87 ppm, -1.2σ)
* [pass] shape: U-shaped: ingress+egress = 0.08 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 6.15 ρ☉ vs catalogue 2.05 ρ☉ (ratio 2.99, 1.3σ)
* [pass] radius: companion radius 0.22 R_Jup
* [pass] coverage: 7 of 8 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (11.39 d) or its multiples
* [pass] centroid: the dip is 8.7″ from the target (2.1σ, 1 sector); stars within 14″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
