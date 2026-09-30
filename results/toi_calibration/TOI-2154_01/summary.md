# TOI-2154.01

* Sectors: 40; 18186 points over 28.2 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.39 R☉, Teff = 6243 K, ρ* = 0.453 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 393 ppm, 1h: 275 ppm, 2h: 211 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 14.10 d, semi-amplitude 88 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 3.82346 | 2404.8141 | 1.80 | 8413 | 89.7 | 9.6 | detected |
| 2 | 0.61942 | 2404.4170 | 2.44 | 165 | 6.2 | 5.9 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.8241222 +0.00014 / −0.00014 |
| T0 (BTJD) | 2404.81499 +0.0003 / −0.00029 |
| Rp/R* | 0.107 +0.0037 / −0.0029 |
| a/R* | 8.1 +0.28 / −0.22 |
| b | 0.874 +0.013 / −0.021 |
| T14 (h) | 2.47 +0.048 / −0.039 |
| depth k² (ppm) | 1.14e+04 +8e+02 / −6.2e+02 |
| ρ* (ρ☉) | 0.488 +0.052 / −0.039 |
| Rp (R⊕) | 16.2 +0.9 / −0.85 |

MCMC: 20000 steps, 34 times the longest autocorrelation time (581 steps); 6720 samples after burn-in and thinning, acceptance 0.29; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 10067±146 ppm vs even 10339±208 ppm: 1.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (108±79 ppm, 1.4σ)
* [pass] shape: intermediate: ingress+egress = 0.65 of the duration; posterior P(grazing) = 0.02
* [pass] density: transit-implied ρ* = 0.49 ρ☉ vs catalogue 0.45 ρ☉ (ratio 1.08, 0.3σ)
* [pass] radius: companion radius 1.44 R_Jup
* [pass] coverage: 6 of 6 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 0.3″ from the target (0.0σ, 1 sector); stars within 9″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
