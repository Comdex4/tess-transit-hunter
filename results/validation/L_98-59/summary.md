# L 98-59

* Sectors: 2, 5, 8, 9, 10, 11, 12, 28, 29, 32, 35, 36, 37, 38, 39, 61, 62, 63, 64, 65, 69, 87, 88, 89, 90, 96, 98; 451939 points over 2691.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.314 R☉, Teff = 3429 K, ρ* = 9.44 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 227 ppm, 1h: 166 ppm, 2h: 127 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 10.84 d, semi-amplitude 65 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 3.69068 | 2371.1366 | 1.18 | 1545 | 132.0 | 71.0 | detected |
| 2 | 7.45073 | 2368.5878 | 0.60 | 1414 | 65.1 | 63.3 | detected |
| 3 | 2.25312 | 2371.0592 | 0.96 | 597 | 62.5 | 73.4 | detected |
| 4 | 1.04918 | 2371.3729 | 1.41 | 196 | 36.7 | 52.8 | detected |
| 5 | 0.52460 | 2370.3193 | 1.17 | 56 | 9.3 | 12.9 | same period as #4 (phase 0.50) |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.6906753 +4.2e-07 / −4e-07 |
| T0 (BTJD) | 2371.13697 +9.4e-05 / −9.4e-05 |
| Rp/R* | 0.0402 +0.0015 / −0.0016 |
| a/R* | 18.5 +3.1 / −2.3 |
| b | 0.611 +0.12 / −0.24 |
| T14 (h) | 1.29 +0.018 / −0.017 |
| depth k² (ppm) | 1.62e+03 +1.2e+02 / −1.2e+02 |
| ρ* (ρ☉) | 6.23 +3.7 / −2.1 |
| Rp (R⊕) | 1.38 +0.065 / −0.063 |

MCMC: 20000 steps, 15 times the longest autocorrelation time (1322 steps); 4560 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1773±19 ppm vs even 1746±19 ppm: 1.0σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-17±15 ppm, -1.2σ)
* [pass] shape: U-shaped: ingress+egress = 0.22 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 6.23 ρ☉ vs catalogue 9.44 ρ☉ (ratio 0.66, 1.0σ)
* [pass] radius: companion radius 0.12 R_Jup
* [pass] coverage: 91 of 155 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.4507294 +1.4e-06 / −1.4e-06 |
| T0 (BTJD) | 2368.58834 +0.00017 / −0.00017 |
| Rp/R* | 0.0453 +0.0029 / −0.0024 |
| a/R* | 40.4 +6.4 / −4.6 |
| b | 0.885 +0.031 / −0.048 |
| T14 (h) | 0.783 +0.028 / −0.029 |
| depth k² (ppm) | 2.05e+03 +2.7e+02 / −2.1e+02 |
| ρ* (ρ☉) | 16 +8.9 / −4.8 |
| Rp (R⊕) | 1.55 +0.11 / −0.098 |

MCMC: 20000 steps, 28 times the longest autocorrelation time (723 steps); 6200 samples after burn-in and thinning, acceptance 0.29; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1649±36 ppm vs even 1664±36 ppm: 0.3σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (9±27 ppm, 0.3σ)
* [pass] shape: intermediate: ingress+egress = 0.57 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 15.98 ρ☉ vs catalogue 9.44 ρ☉ (ratio 1.69, 1.3σ)
* [pass] radius: companion radius 0.14 R_Jup
* [pass] coverage: 53 of 75 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.2531143 +3.5e-07 / −3.4e-07 |
| T0 (BTJD) | 2371.05934 +0.00015 / −0.00014 |
| Rp/R* | 0.0251 +0.00063 / −0.00046 |
| a/R* | 16.7 +1.3 / −2.5 |
| b | 0.395 +0.23 / −0.26 |
| T14 (h) | 0.976 +0.015 / −0.011 |
| depth k² (ppm) | 628 +32 / −23 |
| ρ* (ρ☉) | 12.3 +3.1 / −4.8 |
| Rp (R⊕) | 0.86 +0.032 / −0.03 |

MCMC: 20000 steps, 19 times the longest autocorrelation time (1035 steps); 4840 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 682±16 ppm vs even 696±16 ppm: 0.6σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (10±13 ppm, 0.8σ)
* [pass] shape: U-shaped: ingress+egress = 0.23 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 12.29 ρ☉ vs catalogue 9.44 ρ☉ (ratio 1.30, 0.7σ)
* [pass] radius: companion radius 0.08 R_Jup
* [pass] coverage: 173 of 250 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 4

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.049182 +8.1e-07 / −8.4e-07 |
| T0 (BTJD) | 2371.37309 +0.00069 / −0.00071 |
| Rp/R* | 0.0127 +0.0026 / −0.00077 |
| a/R* | 4.2 +0.36 / −0.81 |
| b | 0.375 +0.31 / −0.26 |
| T14 (h) | 1.81 +0.081 / −0.075 |
| depth k² (ppm) | 160 +74 / −19 |
| ρ* (ρ☉) | 0.9 +0.25 / −0.43 |
| Rp (R⊕) | 0.435 +0.089 / −0.031 |

MCMC: 20000 steps, 16 times the longest autocorrelation time (1277 steps); 4360 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 240±9 ppm vs even 227±9 ppm: 1.0σ difference
* [fail] secondary: significant eclipse at phase 0.5 (37±6 ppm, 6.2σ), deeper than any planetary occultation (≤9 ppm): self-luminous companion
* [pass] shape: intermediate: ingress+egress = 0.64 of the duration; posterior P(grazing) = 0.00
* [fail] density: transit-implied ρ* = 0.90 ρ☉ vs catalogue 9.44 ρ☉ (ratio 0.10, 5.3σ)
* [pass] radius: companion radius 0.04 R_Jup
* [pass] coverage: 495 of 602 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Signal 5 (not a planet)

**secondary eclipse of an eclipsing binary (with signal 4, phase 0.50)**

* [fail] secondary (of signal 4): significant eclipse at phase 0.5 (37±6 ppm, 6.2σ), deeper than any planetary occultation (≤9 ppm): self-luminous companion

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [periodogram_2](periodogram_2.png)
* [fold_2](fold_2.png)
* [periodogram_3](periodogram_3.png)
* [fold_3](fold_3.png)
* [periodogram_4](periodogram_4.png)
* [fold_4](fold_4.png)
* [periodogram_5](periodogram_5.png)
* [fold_5](fold_5.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
* [fit_2](fit_2.png)
* [corner_2](corner_2.png)
* [vetting_2](vetting_2.png)
* [fit_3](fit_3.png)
* [corner_3](corner_3.png)
* [vetting_3](vetting_3.png)
* [fit_4](fit_4.png)
* [corner_4](corner_4.png)
* [vetting_4](vetting_4.png)
