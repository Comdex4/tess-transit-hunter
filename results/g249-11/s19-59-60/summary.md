# TIC 417732194

* Sectors: 19, 59, 60; 44976 points over 1146.5 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.266 R☉, Teff = 3180 K, ρ* = 12.7 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 1090 ppm, 1h: 781 ppm, 2h: 539 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 5.46 d, semi-amplitude 281 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.30742 | 2922.9291 | 0.70 | 2987 | 11.8 | 15.9 | detected |
| 2 | 0.88396 | 2920.7936 | 0.92 | 592 | 6.2 | 7.6 | below threshold |

Dips at the edges of the data masked before the search (2; depth, duration and S/N): BTJD 2955.052 (3024 ppm, 9.2 h, 10.0); BTJD 2955.064 (4007 ppm, 5.3 h, 9.4)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.3074192 +9.4e-06 / −9.6e-06 |
| T0 (BTJD) | 2922.92906 +0.0011 / −0.0012 |
| Rp/R* | 0.0556 +0.013 / −0.0047 |
| a/R* | 43.9 +8.2 / −19 |
| b | 0.526 +0.38 / −0.36 |
| T14 (h) | 0.856 +0.11 / −0.079 |
| depth k² (ppm) | 3.09e+03 +1.6e+03 / −5e+02 |
| ρ* (ρ☉) | 40.3 +27 / −33 |
| Rp (R⊕) | 1.62 +0.39 / −0.15 |

MCMC: 20000 steps, 15 times the longest autocorrelation time (1311 steps); 3920 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 3605±534 ppm vs even 3589±495 ppm: 0.0σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-398±286 ppm, -1.4σ)
* [pass] shape: U-shaped: ingress+egress = 0.09 of the duration; posterior P(grazing) = 0.13
* [pass] density: transit-implied ρ* = 40.27 ρ☉ vs catalogue 12.68 ρ☉ (ratio 3.18, 0.7σ)
* [pass] radius: companion radius 0.14 R_Jup
* [pass] coverage: 13 of 13 transits with data are fully covered (inside and on both sides)
* [pass] momentum_dumps: no transit within 1 h of a momentum dump
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 1.6″ from the target (0.1σ, 2 sectors); stars within 14″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

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
