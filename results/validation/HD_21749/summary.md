# HD 21749

* Sectors: 1, 2, 3, 4, 28, 29, 30, 34, 61, 64, 68, 69, 95, 96, 97; 251162 points over 2663.0 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.705 R☉, Teff = 4629 K, ρ* = 2.08 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 117 ppm, 1h: 93 ppm, 2h: 77 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 7.34 d, semi-amplitude 132 ppm, power 0.03

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 35.61342 | 2240.6492 | 3.11 | 1354 | 63.9 | 24.6 | detected |
| 2 | 7.78981 | 2251.4716 | 2.28 | 215 | 20.0 | 8.1 | detected |
| 3 | 145.68370 | 2304.5204 | 8.25 | 1131 | 45.6 | 10.2 | detected |
| 4 | 109.87728 | 2300.8203 | 6.47 | 952 | 30.2 | 7.7 | detected |
| 5 | 21.35921 | 2248.0685 | 3.10 | 260 | 16.8 | 6.8 | below threshold |

Dips at the edges of the data masked before the search (20; depth, duration and S/N): BTJD 1338.516 (1466 ppm, 0.6 h, 10.6); BTJD 1385.964 (934 ppm, 0.7 h, 11.5); BTJD 1394.436 (234 ppm, 9.2 h, 7.7); BTJD 1394.513 (242 ppm, 11.1 h, 7.1); BTJD 1416.989 (4220 ppm, 0.5 h, 8.6); BTJD 1422.516 (3466 ppm, 0.5 h, 7.9); BTJD 2987.811 (528 ppm, 9.2 h, 23.3); BTJD 2987.824 (940 ppm, 4.5 h, 21.5); BTJD 3041.120 (1938 ppm, 0.5 h, 12.9); BTJD 3154.838 (5393 ppm, 1.0 h, 47.7); BTJD 3154.849 (4608 ppm, 1.0 h, 45.5); BTJD 3201.489 (252 ppm, 6.4 h, 8.4); BTJD 3894.177 (740 ppm, 7.7 h, 19.3); BTJD 3901.078 (296 ppm, 7.7 h, 7.8); BTJD 3907.032 (594 ppm, 9.2 h, 17.0); BTJD 3914.475 (1064 ppm, 3.1 h, 24.1); BTJD 3936.383 (1423 ppm, 2.1 h, 22.5); BTJD 3936.391 (1266 ppm, 3.7 h, 23.0); BTJD 3950.124 (977 ppm, 1.2 h, 11.0); BTJD 3967.391 (1111 ppm, 0.5 h, 7.8)

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 287.38935 d, SDE 8.8: only 1 transit(s) with data
* iteration 4: P = 285.17976 d, SDE 9.1: only 1 transit(s) with data
* iteration 4: P = 318.21444 d, SDE 8.4: only 1 transit(s) with data
* iteration 4: P = 375.77263 d, SDE 10.4: only 1 transit(s) with data
* iteration 4: P = 363.67527 d, SDE 10.5: only 1 transit(s) with data
* iteration 5: P = 138.32384 d, SDE 8.3: only 1 transit(s) with data
* iteration 5: P = 165.98758 d, SDE 8.0: only 1 transit(s) with data
* iteration 5: P = 143.20766 d, SDE 7.1: folded light curve also brightens (63.8 sigma, against 66.0 sigma for the dip): stellar variability
* iteration 5: P = 136.52969 d, SDE 8.3: only 1 transit(s) with data
* iteration 5: P = 156.22704 d, SDE 7.0: folded light curve also brightens (58.8 sigma, against 64.7 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 35.613446 +1.6e-05 / −1.7e-05 |
| T0 (BTJD) | 2240.64832 +0.00042 / −0.00041 |
| Rp/R* | 0.0362 +0.0015 / −0.00099 |
| a/R* | 76 +9.3 / −11 |
| b | 0.487 +0.18 / −0.3 |
| T14 (h) | 3.28 +0.056 / −0.045 |
| depth k² (ppm) | 1.31e+03 +1.1e+02 / −71 |
| ρ* (ρ☉) | 4.65 +1.9 / −1.7 |
| Rp (R⊕) | 2.8 +0.26 / −0.27 |

MCMC: 20000 steps, 23 times the longest autocorrelation time (878 steps); 5240 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [note] left out before the fit and the tests, as far from the depth of the other 8 measured transits (median 1465 ppm, scatter 104 ppm): BTJD 1421.540: 4870±161 ppm deep, data on one side only
* [pass] odd_even: odd depth 1459±37 ppm vs even 1420±64 ppm: 0.5σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-14±24 ppm, -0.6σ); a 192 ppm dip at phase 0.11 (8.0σ) comes from a single orbit and is not counted
* [pass] shape: U-shaped: ingress+egress = 0.21 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 4.65 ρ☉ vs catalogue 2.08 ρ☉ (ratio 2.24, 1.4σ)
* [pass] radius: companion radius 0.25 R_Jup
* [pass] coverage: 8 of 8 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.7897719 +1e-05 / −1.4e-05 |
| T0 (BTJD) | 2251.47513 +0.0016 / −0.0014 |
| Rp/R* | 0.0125 +0.0022 / −0.00085 |
| a/R* | 19.7 +3 / −6.9 |
| b | 0.503 +0.33 / −0.34 |
| T14 (h) | 2.65 +0.14 / −0.097 |
| depth k² (ppm) | 156 +61 / −21 |
| ρ* (ρ☉) | 1.7 +0.89 / −1.2 |
| Rp (R⊕) | 0.975 +0.18 / −0.11 |

MCMC: 20000 steps, 18 times the longest autocorrelation time (1105 steps); 3840 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [note] left out before the fit and the tests, as far from the depth of the other 42 measured transits (median 179 ppm, scatter 119 ppm): BTJD 1433.542: 3499±119 ppm deep, out-of-transit level -606 ppm higher before than after; BTJD 1425.752: 807±122 ppm deep, out-of-transit level +1439 ppm higher before than after
* [pass] odd_even: odd depth 244±25 ppm vs even 164±22 ppm: 2.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (22±12 ppm, 1.8σ); a 83 ppm dip at phase 0.40 (6.8σ) comes from a single orbit and is not counted
* [pass] shape: U-shaped: ingress+egress = 0.46 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 1.70 ρ☉ vs catalogue 2.08 ρ☉ (ratio 0.82, 0.4σ)
* [pass] radius: companion radius 0.09 R_Jup
* [pass] coverage: 40 of 42 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 145.69619 +0.00052 / −0.00053 |
| T0 (BTJD) | 2304.58808 +0.0037 / −0.0039 |
| Rp/R* | 0.386 +0.36 / −0.23 |
| a/R* | 35.4 +3.1 / −3 |
| b | 1.29 +0.37 / −0.25 |
| T14 (h) | 15.9 +0.68 / −0.58 |
| depth k² (ppm) | 1.49e+05 +4e+05 / −1.2e+05 |
| ρ* (ρ☉) | 0.0279 +0.0081 / −0.0066 |
| Rp (R⊕) | 29.3 +27 / −17 |

MCMC: 20000 steps, 10 times the longest autocorrelation time (2069 steps); 1840 samples after burn-in and thinning, acceptance 0.14; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [n/a] odd_even: need at least one odd and one even transit
* [pass] secondary: no significant eclipse at phase 0.5 (18±14 ppm, 1.3σ); a 516 ppm dip at phase 0.91 (24.9σ) comes from a single orbit and is not counted
* [warn] shape: V-shaped: ingress+egress = 0.81 of the duration; posterior P(grazing) = 1.00
* [fail] density: transit-implied ρ* = 0.03 ρ☉ vs catalogue 2.08 ρ☉ (ratio 0.01, 11.7σ)
* [fail] radius: companion radius 2.65 R_Jup
* [warn] coverage: 1 of 2 transits with data are fully covered (inside and on both sides): the signal rests on one complete transit
* [n/a] rotation: no clear rotational modulation

## Candidate 4

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 109.86132 +0.0035 / −0.0036 |
| T0 (BTJD) | 2300.74359 +0.026 / −0.026 |
| Rp/R* | 0.131 +0.46 / −0.077 |
| a/R* | 22.9 +12 / −2.6 |
| b | 1.05 +0.48 / −0.16 |
| T14 (h) | 16 +1.2 / −2 |
| depth k² (ppm) | 1.71e+04 +3.3e+05 / −1.4e+04 |
| ρ* (ρ☉) | 0.0134 +0.035 / −0.0041 |
| Rp (R⊕) | 9.78 +36 / −5.8 |

MCMC: 20000 steps, 8 times the longest autocorrelation time (2430 steps); 1560 samples after burn-in and thinning, acceptance 0.15; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [n/a] odd_even: need at least one odd and one even transit
* [fail] secondary: no eclipse at phase 0.5 (-8±13 ppm, -0.6σ), but a 101 ppm dip (8.9σ) at phase 0.04, deeper than any planetary occultation (≤33 ppm): eccentric eclipsing binary?; a 175 ppm dip at phase 0.91 (16.4σ) comes from a single orbit and is not counted
* [warn] shape: intermediate: ingress+egress = 0.65 of the duration; posterior P(grazing) = 0.74
* [fail] density: transit-implied ρ* = 0.01 ρ☉ vs catalogue 2.08 ρ☉ (ratio 0.01, 5.1σ)
* [pass] radius: companion radius 0.90 R_Jup
* [warn] coverage: 1 of 2 transits with data are fully covered (inside and on both sides): the signal rests on one complete transit
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
