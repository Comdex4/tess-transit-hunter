# SYN-4 (synthetic)

> **Synthetic light curve** – not a real star.

* Sectors: 1, 2, 3, 4, 5, 6; 114052 points over 164.4 days
* Host star (synthetic star (truth, with 3 % / 5 % radius / mass uncertainties)): R* = 0.7 R☉, Teff = 4600 K, ρ* = 2.13 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 84 ppm, 1h: 62 ppm, 2h: 46 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 30.44 d, semi-amplitude 1089 ppm, power 0.79

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 35.59899 | 2081.4998 | 4.21 | 1386 | 90.0 | 18.5 | detected |
| 2 | 0.59601 | 2082.3518 | 3.43 | 12 | 4.9 | 6.0 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 35.59962 +0.00021 / −0.00022 |
| T0 (BTJD) | 2081.49939 +0.00031 / −0.0003 |
| Rp/R* | 0.0375 +0.00093 / −0.00072 |
| a/R* | 57.5 +5.5 / −5.3 |
| b | 0.454 +0.14 / −0.25 |
| T14 (h) | 4.42 +0.044 / −0.039 |
| depth k² (ppm) | 1.41e+03 +71 / −53 |
| ρ* (ρ☉) | 2.01 +0.63 / −0.51 |
| Rp (R⊕) | 2.87 +0.11 / −0.1 |

MCMC: 20000 steps, 19 times the longest autocorrelation time (1053 steps); 5120 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1589±26 ppm vs even 1615±21 ppm: 0.8σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (31±20 ppm, 1.6σ)
* [pass] shape: U-shaped: ingress+egress = 0.21 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 2.01 ρ☉ vs catalogue 2.13 ρ☉ (ratio 0.95, 0.2σ)
* [pass] radius: companion radius 0.26 R_Jup
* [pass] coverage: 5 of 5 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (30.44 d) or its multiples

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
