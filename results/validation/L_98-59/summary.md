# L 98-59

* Sectors: 2, 5, 8, 9, 10, 11, 12, 28, 29, 32, 35, 36, 37, 38, 39, 61, 62, 63, 64, 65, 69, 87, 88, 89, 90, 96, 98; 451939 points over 2691.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.314 R☉, Teff = 3429 K, ρ* = 9.44 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 227 ppm, 1h: 166 ppm, 2h: 127 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 10.84 d, semi-amplitude 65 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 3.69068 | 2371.1366 | 1.18 | 1549 | 131.5 | 69.7 | detected |
| 2 | 7.45073 | 2368.5878 | 0.60 | 1413 | 64.8 | 60.9 | detected |
| 3 | 2.25312 | 2371.0592 | 0.96 | 597 | 62.5 | 73.2 | detected |
| 4 | 1.04918 | 2370.3237 | 1.41 | 197 | 36.8 | 56.3 | detected |
| 5 | 0.52460 | 2370.3193 | 1.17 | 56 | 9.4 | 15.2 | same period as #4 (phase 0.50) |

Dips at the edges of the data masked before the search (6; depth, duration and S/N): BTJD 1535.049 (670 ppm, 5.3 h, 9.5); BTJD 1535.060 (453 ppm, 7.7 h, 9.0); BTJD 1555.506 (1208 ppm, 1.0 h, 7.4); BTJD 2374.832 (1208 ppm, 1.5 h, 8.6); BTJD 3002.797 (596 ppm, 4.5 h, 7.6); BTJD 3933.237 (1435 ppm, 0.9 h, 8.9)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.6906754 +4e-07 / −4e-07 |
| T0 (BTJD) | 2371.13694 +0.0001 / −0.0001 |
| Rp/R* | 0.0399 +0.0016 / −0.0014 |
| a/R* | 19.1 +3.1 / −2.5 |
| b | 0.571 +0.14 / −0.29 |
| T14 (h) | 1.28 +0.019 / −0.018 |
| depth k² (ppm) | 1.59e+03 +1.3e+02 / −1.1e+02 |
| ρ* (ρ☉) | 6.91 +3.9 / −2.4 |
| Rp (R⊕) | 1.37 +0.067 / −0.061 |

MCMC: 20000 steps, 19 times the longest autocorrelation time (1046 steps); 4560 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1808±26 ppm vs even 1756±26 ppm: 1.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-17±15 ppm, -1.2σ)
* [pass] shape: U-shaped: ingress+egress = 0.35 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 6.91 ρ☉ vs catalogue 9.44 ρ☉ (ratio 0.73, 0.6σ)
* [pass] radius: companion radius 0.12 R_Jup
* [pass] coverage: 91 of 153 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.4507293 +1.4e-06 / −1.3e-06 |
| T0 (BTJD) | 2368.58833 +0.00017 / −0.00017 |
| Rp/R* | 0.0448 +0.0029 / −0.0027 |
| a/R* | 41.1 +7.9 / −4.4 |
| b | 0.881 +0.03 / −0.063 |
| T14 (h) | 0.776 +0.027 / −0.03 |
| depth k² (ppm) | 2.01e+03 +2.7e+02 / −2.3e+02 |
| ρ* (ρ☉) | 16.8 +12 / −4.8 |
| Rp (R⊕) | 1.53 +0.11 / −0.1 |

MCMC: 20000 steps, 22 times the longest autocorrelation time (894 steps); 5720 samples after burn-in and thinning, acceptance 0.27; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1580±49 ppm vs even 1614±51 ppm: 0.5σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (12±27 ppm, 0.4σ)
* [pass] shape: intermediate: ingress+egress = 0.52 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 16.78 ρ☉ vs catalogue 9.44 ρ☉ (ratio 1.78, 1.6σ)
* [pass] radius: companion radius 0.14 R_Jup
* [pass] coverage: 53 of 74 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.2531143 +3.4e-07 / −3.3e-07 |
| T0 (BTJD) | 2371.05934 +0.00016 / −0.00014 |
| Rp/R* | 0.025 +0.0006 / −0.00044 |
| a/R* | 16.8 +1.2 / −2.4 |
| b | 0.385 +0.23 / −0.26 |
| T14 (h) | 0.976 +0.014 / −0.011 |
| depth k² (ppm) | 627 +30 / −22 |
| ρ* (ρ☉) | 12.5 +2.9 / −4.6 |
| Rp (R⊕) | 0.86 +0.033 / −0.03 |

MCMC: 20000 steps, 22 times the longest autocorrelation time (912 steps); 5560 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 708±22 ppm vs even 728±23 ppm: 0.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (11±13 ppm, 0.8σ)
* [pass] shape: U-shaped: ingress+egress = 0.23 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 12.53 ρ☉ vs catalogue 9.44 ρ☉ (ratio 1.33, 0.6σ)
* [pass] radius: companion radius 0.08 R_Jup
* [pass] coverage: 173 of 250 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 4

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.049182 +7.7e-07 / −8.5e-07 |
| T0 (BTJD) | 2371.37278 +0.00074 / −0.00076 |
| Rp/R* | 0.0193 +0.014 / −0.0071 |
| a/R* | 2.05 +2.3 / −0.62 |
| b | 0.921 +0.074 / −0.68 |
| T14 (h) | 1.98 +0.2 / −0.2 |
| depth k² (ppm) | 372 +7.6e+02 / −2.2e+02 |
| ρ* (ρ☉) | 0.106 +0.9 / −0.071 |
| Rp (R⊕) | 0.656 +0.49 / −0.24 |

MCMC: 20000 steps, 9 times the longest autocorrelation time (2124 steps); 1960 samples after burn-in and thinning, acceptance 0.13; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 242±12 ppm vs even 234±12 ppm: 0.5σ difference (uncertainties include the 203 ppm scatter between transits)
* [pass] secondary: eclipse at phase 0.5 (37±6 ppm, 6.6σ) is within the planetary maximum (107 ppm): consistent with a hot planet's occultation
* [pass] shape: intermediate: ingress+egress = 0.65 of the duration; posterior P(grazing) = 0.38
* [fail] density: transit-implied ρ* = 0.10 ρ☉ vs catalogue 9.44 ρ☉ (ratio 0.01, 91.7σ)
* [pass] radius: companion radius 0.06 R_Jup
* [pass] coverage: 484 of 604 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Signal 5 (not a planet)

**occultation of signal 4 (phase 0.50), consistent with a planet**

* [pass] secondary (of signal 4): eclipse at phase 0.5 (37±6 ppm, 6.6σ) is within the planetary maximum (107 ppm): consistent with a hot planet's occultation

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
