# TIC 417732194

* Sectors: 59, 60; 28633 points over 50.7 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.266 R☉, Teff = 3180 K, ρ* = 12.7 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 1169 ppm, 1h: 787 ppm, 2h: 575 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 5.39 d, semi-amplitude 397 ppm, power 0.04

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.30674 | 2933.5436 | 0.70 | 3042 | 9.5 | 10.8 | detected |
| 2 | 1.81088 | 2935.0851 | 1.41 | 837 | 5.5 | 5.7 | below threshold |

Dips at the edges of the data masked before the search (2; depth, duration and S/N): BTJD 2955.082 (3778 ppm, 5.3 h, 9.9); BTJD 2955.131 (2386 ppm, 9.2 h, 9.3)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.3078264 +0.00057 / −0.00057 |
| T0 (BTJD) | 2933.54347 +0.0014 / −0.0016 |
| Rp/R* | 0.0593 +0.38 / −0.0093 |
| a/R* | 36.1 +19 / −18 |
| b | 0.773 +0.59 / −0.51 |
| T14 (h) | 0.843 +0.2 / −0.12 |
| depth k² (ppm) | 3.52e+03 +1.9e+05 / −1e+03 |
| ρ* (ρ☉) | 22.3 +56 / −20 |
| Rp (R⊕) | 1.72 +11 / −0.28 |

MCMC: 20000 steps, 12 times the longest autocorrelation time (1738 steps); 3160 samples after burn-in and thinning, acceptance 0.19; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 3244±670 ppm vs even 2527±670 ppm: 0.8σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-383±378 ppm, -1.0σ)
* [pass] shape: U-shaped: ingress+egress = 0.16 of the duration; posterior P(grazing) = 0.40
* [pass] density: transit-implied ρ* = 22.33 ρ☉ vs catalogue 12.68 ρ☉ (ratio 1.76, 0.2σ)
* [pass] radius: companion radius 0.15 R_Jup
* [pass] coverage: 8 of 8 transits with data are fully covered (inside and on both sides)
* [pass] momentum_dumps: no transit within 1 h of a momentum dump
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 5.8″ from the target (0.8σ, 1 sector); stars within 15″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [periodogram_2](periodogram_2.png)
* [fold_2](fold_2.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
