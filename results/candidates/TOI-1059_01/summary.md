# TOI-1059.01

* Sectors: 13, 39, 66, 93, 100, 102, 103, 104; 133441 points over 2550.6 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.944 R☉, Teff = 5188 K, ρ* = 1.05 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 506 ppm, 1h: 387 ppm, 2h: 325 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 10.24 d, semi-amplitude 7092 ppm, power 0.34

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 9.44966 | 3852.8614 | 1.42 | 18957 | 235.8 | 37.0 | detected |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 9.4496543 +8.5e-07 / −8.6e-07 |
| T0 (BTJD) | 3852.86089 +9.9e-05 / −0.0001 |
| Rp/R* | 0.475 +0.32 / −0.21 |
| a/R* | 25.4 +1.3 / −0.88 |
| b | 1.25 +0.33 / −0.24 |
| T14 (h) | 2.27 +0.035 / −0.031 |
| depth k² (ppm) | 2.25e+05 +4e+05 / −1.5e+05 |
| ρ* (ρ☉) | 2.47 +0.39 / −0.25 |
| Rp (R⊕) | 48.9 +32 / −21 |

MCMC: 20000 steps, 10 times the longest autocorrelation time (2013 steps); 1960 samples after burn-in and thinning, acceptance 0.15; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 24760±172 ppm vs even 24322±146 ppm: 1.9σ difference
* [warn] secondary: no eclipse at phase 0.5 (89±87 ppm, 1.0σ); strongest dip at phase 0.07: 611 ppm (7.4σ)
* [warn] shape: intermediate: ingress+egress = 0.79 of the duration; posterior P(grazing) = 1.00
* [warn] density: transit-implied ρ* = 2.47 ρ☉ vs catalogue 1.05 ρ☉ (ratio 2.36, 3.1σ)
* [fail] radius: companion radius 4.36 R_Jup
* [pass] coverage: 19 of 19 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (10.24 d) or its multiples

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
