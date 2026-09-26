# HD 21749

* Sectors: 1, 2, 3, 4, 28, 29, 30, 34, 61, 64, 68, 69, 95, 96, 97; 251162 points over 2663.0 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.705 R☉, Teff = 4629 K, ρ* = 2.08 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 117 ppm, 1h: 93 ppm, 2h: 77 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 7.34 d, semi-amplitude 137 ppm, power 0.03

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 35.61342 | 2240.6492 | 2.92 | 1324 | 62.4 | 17.5 | detected |
| 2 | 193.09210 | 2189.3800 | 2.70 | 3564 | 73.7 | 9.0 | detected |
| 3 | 139.04745 | 2267.7975 | 3.50 | 1831 | 42.3 | 5.9 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 3: P = 113.90314 d, SDE 8.3: only 1 transit(s) with data
* iteration 3: P = 156.61679 d, SDE 7.0: only 1 transit(s) with data
* iteration 3: P = 107.12295 d, SDE 6.5: only 1 transit(s) with data
* iteration 3: P = 198.14717 d, SDE 3.7: only 1 transit(s) with data
* iteration 3: P = 227.80685 d, SDE 6.5: only 1 transit(s) with data
* iteration 3: P = 208.82227 d, SDE 6.2: only 1 transit(s) with data
* iteration 3: P = 109.41738 d, SDE 6.2: only 1 transit(s) with data
* iteration 3: P = 111.39894 d, SDE 6.1: only 1 transit(s) with data
* iteration 3: P = 105.21677 d, SDE 6.0: only 1 transit(s) with data
* iteration 3: P = 98.91320 d, SDE 5.9: only 1 transit(s) with data
* iteration 3: P = 214.23927 d, SDE 4.1: only 1 transit(s) with data

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 35.613408 +2.3e-05 / −2.5e-05 |
| T0 (BTJD) | 2240.6485 +0.00062 / −0.00061 |
| Rp/R* | 0.0377 +0.0023 / −0.0018 |
| a/R* | 67.2 +15 / −13 |
| b | 0.633 +0.14 / −0.32 |
| T14 (h) | 3.34 +0.11 / −0.077 |
| depth k² (ppm) | 1.42e+03 +1.8e+02 / −1.4e+02 |
| ρ* (ρ☉) | 3.2 +2.6 / −1.5 |
| Rp (R⊕) | 2.91 +0.3 / −0.3 |

MCMC: 20000 steps, 18 times the longest autocorrelation time (1124 steps); 4760 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 1769±25 ppm vs even 1306±42 ppm: 9.4σ difference
* [fail] secondary: no eclipse at phase 0.5 (-12±24 ppm, -0.5σ), but a 270 ppm dip (11.4σ) at phase 0.34, deeper than any planetary occultation (≤0 ppm): eccentric eclipsing binary?
* [pass] shape: U-shaped: ingress+egress = 0.40 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 3.20 ρ☉ vs catalogue 2.08 ρ☉ (ratio 1.54, 0.6σ)
* [pass] radius: companion radius 0.26 R_Jup
* [pass] coverage: 9 of 12 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 193.09293 +0.00021 / −0.00021 |
| T0 (BTJD) | 2189.37418 +0.001 / −0.0011 |
| Rp/R* | 0.529 +0.32 / −0.26 |
| a/R* | 199 +16 / −17 |
| b | 1.41 +0.32 / −0.27 |
| T14 (h) | 4.32 +0.21 / −0.18 |
| depth k² (ppm) | 2.8e+05 +4.3e+05 / −2.1e+05 |
| ρ* (ρ☉) | 2.84 +0.76 / −0.66 |
| Rp (R⊕) | 40.6 +25 / −20 |

MCMC: 20000 steps, 13 times the longest autocorrelation time (1508 steps); 2920 samples after burn-in and thinning, acceptance 0.18; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 5150±106 ppm vs even 5364±113 ppm: 1.4σ difference
* [fail] secondary: no eclipse at phase 0.5 (67±49 ppm, 1.4σ), but a 1025 ppm dip (19.5σ) at phase 0.07, deeper than any planetary occultation (≤7 ppm): eccentric eclipsing binary?
* [warn] shape: V-shaped: ingress+egress = 0.94 of the duration; posterior P(grazing) = 1.00
* [pass] density: transit-implied ρ* = 2.84 ρ☉ vs catalogue 2.08 ρ☉ (ratio 1.37, 0.7σ)
* [fail] radius: companion radius 3.63 R_Jup
* [fail] coverage: 0 of 3 transits with data are fully covered (inside and on both sides): every event lies at the edge of a data segment, where instrumental systematics are common
* [n/a] rotation: no clear rotational modulation

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [periodogram_2](periodogram_2.png)
* [fold_2](fold_2.png)
* [periodogram_3](periodogram_3.png)
* [fold_3](fold_3.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
* [fit_2](fit_2.png)
* [corner_2](corner_2.png)
* [vetting_2](vetting_2.png)
