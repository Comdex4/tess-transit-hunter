# pi Men

* Sectors: 1, 4, 8, 11, 12, 13, 27, 28, 31, 34, 38, 39, 61, 62, 64, 65, 66, 67, 68, 88, 89, 93, 94, 95; 393006 points over 2581.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.15 R☉, Teff = 5992 K, ρ* = 0.725 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 47 ppm, 1h: 36 ppm, 2h: 27 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 9.58 d, semi-amplitude 15 ppm, power 0.01

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 6.26781 | 2391.0347 | 2.92 | 251 | 106.6 | 34.9 | detected |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 6.2678218 +1e-06 / −1e-06 |
| T0 (BTJD) | 2391.03428 +0.00014 / −0.00015 |
| Rp/R* | 0.0166 +0.00036 / −0.00022 |
| a/R* | 15.1 +1.1 / −1.7 |
| b | 0.392 +0.19 / −0.25 |
| T14 (h) | 2.98 +0.014 / −0.012 |
| depth k² (ppm) | 275 +12 / −7.2 |
| ρ* (ρ☉) | 1.17 +0.28 / −0.36 |
| Rp (R⊕) | 2.08 +0.091 / −0.089 |

MCMC: 20000 steps, 15 times the longest autocorrelation time (1354 steps); 4440 samples after burn-in and thinning, acceptance 0.21; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 309±4 ppm vs even 311±3 ppm: 0.3σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (1±3 ppm, 0.4σ)
* [pass] shape: U-shaped: ingress+egress = 0.22 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 1.17 ρ☉ vs catalogue 0.73 ρ☉ (ratio 1.61, 1.4σ)
* [pass] radius: companion radius 0.19 R_Jup
* [pass] coverage: 90 of 93 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
