# L 98-59

* Sectors: 2, 5, 8, 9, 10, 11, 12, 28, 29, 32, 35, 36, 37, 38, 39, 61, 62, 63, 64, 65, 69, 87, 88, 89, 90, 96, 98; 451939 points over 2691.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.314 R☉, Teff = 3429 K, ρ* = 9.44 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 227 ppm, 1h: 166 ppm, 2h: 127 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 10.84 d, semi-amplitude 65 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 3.69068 | 2371.1366 | 1.18 | 1551 | 130.9 | 69.6 | detected |
| 2 | 7.45073 | 2368.5878 | 0.60 | 1408 | 63.8 | 60.5 | detected |
| 3 | 2.25312 | 2371.0592 | 0.96 | 597 | 62.5 | 73.6 | detected |
| 4 | 1.04918 | 2370.3237 | 1.41 | 197 | 36.7 | 58.5 | detected |
| 5 | 0.52460 | 2370.3193 | 1.17 | 56 | 9.4 | 15.3 | same period as #4 (phase 0.50) |

Dips at the edges of the data masked before the search (14; depth, duration and S/N): BTJD 1459.591 (1697 ppm, 1.0 h, 8.7); BTJD 1535.049 (670 ppm, 5.3 h, 9.5); BTJD 1535.060 (453 ppm, 7.7 h, 9.0); BTJD 1555.506 (1208 ppm, 1.0 h, 7.4); BTJD 2374.832 (1208 ppm, 1.5 h, 8.6); BTJD 3002.797 (596 ppm, 4.5 h, 7.6); BTJD 3083.436 (1609 ppm, 1.0 h, 10.0); BTJD 3188.170 (1747 ppm, 0.5 h, 7.9); BTJD 3703.876 (1595 ppm, 0.6 h, 7.7); BTJD 3703.880 (1676 ppm, 0.7 h, 8.0); BTJD 3703.882 (1780 ppm, 0.6 h, 7.5); BTJD 3718.141 (1220 ppm, 1.2 h, 7.3); BTJD 3933.237 (1435 ppm, 0.9 h, 8.9); BTJD 4009.804 (1297 ppm, 1.8 h, 8.3)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.6906754 +4.2e-07 / −4.3e-07 |
| T0 (BTJD) | 2371.13696 +0.0001 / −0.0001 |
| Rp/R* | 0.0399 +0.0017 / −0.0014 |
| a/R* | 19.3 +3.2 / −2.6 |
| b | 0.559 +0.14 / −0.32 |
| T14 (h) | 1.28 +0.019 / −0.02 |
| depth k² (ppm) | 1.59e+03 +1.4e+02 / −1.1e+02 |
| ρ* (ρ☉) | 7.06 +4.1 / −2.5 |
| Rp (R⊕) | 1.37 +0.068 / −0.059 |

MCMC: 20000 steps, 16 times the longest autocorrelation time (1249 steps); 4320 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1813±27 ppm vs even 1759±26 ppm: 1.4σ difference (uncertainties include the 224 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (-18±15 ppm, -1.2σ)
* [pass] shape: U-shaped: ingress+egress = 0.35 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 7.06 ρ☉ vs catalogue 9.44 ρ☉ (ratio 0.75, 0.6σ)
* [pass] radius: companion radius 0.12 R_Jup
* [pass] coverage: 90 of 151 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.4507294 +1.3e-06 / −1.4e-06 |
| T0 (BTJD) | 2368.58833 +0.00017 / −0.00017 |
| Rp/R* | 0.045 +0.0027 / −0.0023 |
| a/R* | 40.7 +6.6 / −4.5 |
| b | 0.884 +0.03 / −0.05 |
| T14 (h) | 0.779 +0.027 / −0.029 |
| depth k² (ppm) | 2.03e+03 +2.5e+02 / −2.1e+02 |
| ρ* (ρ☉) | 16.3 +9.3 / −4.8 |
| Rp (R⊕) | 1.54 +0.1 / −0.093 |

MCMC: 20000 steps, 28 times the longest autocorrelation time (725 steps); 6160 samples after burn-in and thinning, acceptance 0.29; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1580±48 ppm vs even 1618±50 ppm: 0.5σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (11±27 ppm, 0.4σ)
* [pass] shape: U-shaped: ingress+egress = 0.48 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 16.31 ρ☉ vs catalogue 9.44 ρ☉ (ratio 1.73, 1.5σ)
* [pass] radius: companion radius 0.14 R_Jup
* [pass] coverage: 53 of 74 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.2531143 +3.4e-07 / −3.5e-07 |
| T0 (BTJD) | 2371.05933 +0.00017 / −0.00014 |
| Rp/R* | 0.0251 +0.00065 / −0.00046 |
| a/R* | 16.7 +1.3 / −2.6 |
| b | 0.39 +0.24 / −0.26 |
| T14 (h) | 0.975 +0.015 / −0.011 |
| depth k² (ppm) | 630 +33 / −23 |
| ρ* (ρ☉) | 12.4 +3 / −4.9 |
| Rp (R⊕) | 0.861 +0.034 / −0.03 |

MCMC: 20000 steps, 17 times the longest autocorrelation time (1162 steps); 4480 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 702±22 ppm vs even 723±23 ppm: 0.6σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (11±13 ppm, 0.8σ)
* [pass] shape: U-shaped: ingress+egress = 0.24 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 12.42 ρ☉ vs catalogue 9.44 ρ☉ (ratio 1.31, 0.6σ)
* [pass] radius: companion radius 0.08 R_Jup
* [pass] coverage: 173 of 250 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 4

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.0491818 +8.5e-07 / −8.3e-07 |
| T0 (BTJD) | 2370.32358 +0.00065 / −0.00071 |
| Rp/R* | 0.0157 +0.014 / −0.0035 |
| a/R* | 3.31 +1.1 / −1.8 |
| b | 0.703 +0.27 / −0.5 |
| T14 (h) | 1.89 +0.26 / −0.13 |
| depth k² (ppm) | 246 +6.1e+02 / −99 |
| ρ* (ρ☉) | 0.441 +0.62 / −0.4 |
| Rp (R⊕) | 0.54 +0.45 / −0.12 |

MCMC: 20000 steps, 9 times the longest autocorrelation time (2143 steps); 2000 samples after burn-in and thinning, acceptance 0.14; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 239±12 ppm vs even 245±12 ppm: 0.3σ difference
* [pass] secondary: eclipse at phase 0.5 (37±6 ppm, 6.4σ) is within the planetary maximum (24 ppm): consistent with a hot planet's occultation
* [pass] shape: intermediate: ingress+egress = 0.66 of the duration; posterior P(grazing) = 0.19
* [fail] density: transit-implied ρ* = 0.44 ρ☉ vs catalogue 9.44 ρ☉ (ratio 0.05, 91.2σ)
* [pass] radius: companion radius 0.05 R_Jup
* [pass] coverage: 488 of 603 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Signal 5 (not a planet)

**occultation of signal 4 (phase 0.50), consistent with a planet**

* [pass] secondary (of signal 4): eclipse at phase 0.5 (37±6 ppm, 6.4σ) is within the planetary maximum (24 ppm): consistent with a hot planet's occultation

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
