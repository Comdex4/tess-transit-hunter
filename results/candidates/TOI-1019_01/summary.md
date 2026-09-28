# TOI-1019.01

* Sectors: 34, 35, 36, 61, 62, 63, 88, 89, 90; 150487 points over 1546.1 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.56 R☉, Teff = 7645 K, ρ* = 0.47 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 460 ppm, 1h: 325 ppm, 2h: 210 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 8.62 d, semi-amplitude 164 ppm, power 0.04

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.23409 | 3012.3284 | 2.90 | 18414 | 683.0 | 28.1 | detected |

Dips at the edges of the data masked before the search (2; depth, duration and S/N): BTJD 2295.235 (16197 ppm, 3.7 h, 80.9); BTJD 3739.928 (5982 ppm, 0.6 h, 14.5)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.2340995 +6e-07 / −5.8e-07 |
| T0 (BTJD) | 3012.32775 +6.7e-05 / −6.6e-05 |
| Rp/R* | 0.143 +0.00077 / −0.001 |
| a/R* | 9.76 +0.059 / −0.057 |
| b | 0.71 +0.0055 / −0.006 |
| T14 (h) | 3.69 +0.011 / −0.01 |
| depth k² (ppm) | 2.06e+04 +2.2e+02 / −2.9e+02 |
| ρ* (ρ☉) | 0.455 +0.0083 / −0.008 |
| Rp (R⊕) | 24.4 +0.76 / −0.78 |

MCMC: 19500 steps, 63 times the longest autocorrelation time (311 steps); 11440 samples after burn-in and thinning, acceptance 0.37; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 20785±57 ppm vs even 20839±59 ppm: 0.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (22±31 ppm, 0.7σ)
* [pass] shape: U-shaped: ingress+egress = 0.45 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.46 ρ☉ vs catalogue 0.47 ρ☉ (ratio 0.97, 0.2σ)
* [pass] radius: companion radius 2.18 R_Jup
* [pass] coverage: 39 of 39 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
