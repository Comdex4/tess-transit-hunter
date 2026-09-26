# TOI-1717.01

* Sectors: 20, 47, 60, 73; 58893 points over 1470.1 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.36 R☉, Teff = 6578 K, ρ* = 0.549 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 910 ppm, 1h: 906 ppm, 2h: 822 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 0.30 d, semi-amplitude 1136 ppm, power 0.79

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 4.05239 | 2601.3420 | 2.02 | 7628 | 42.0 | 23.7 | detected |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 4.0523835 +9.5e-07 / −9.2e-07 |
| T0 (BTJD) | 2601.34215 +0.00013 / −0.00013 |
| Rp/R* | 0.095 +0.0014 / −0.00092 |
| a/R* | 8.61 +0.16 / −0.17 |
| b | 0.825 +0.011 / −0.011 |
| T14 (h) | 2.6 +0.016 / −0.015 |
| depth k² (ppm) | 9.03e+03 +2.7e+02 / −1.7e+02 |
| ρ* (ρ☉) | 0.521 +0.03 / −0.03 |
| Rp (R⊕) | 14.1 +0.63 / −0.63 |

MCMC: 19000 steps, 68 times the longest autocorrelation time (280 steps); 10080 samples after burn-in and thinning, acceptance 0.36; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 8597±273 ppm vs even 8675±314 ppm: 0.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-115±215 ppm, -0.5σ)
* [pass] shape: U-shaped: ingress+egress = 0.46 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.52 ρ☉ vs catalogue 0.55 ρ☉ (ratio 0.95, 0.2σ)
* [pass] radius: companion radius 1.25 R_Jup
* [pass] coverage: 21 of 21 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (0.30 d) or its multiples

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
