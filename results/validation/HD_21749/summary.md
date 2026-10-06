# HD 21749

* Sectors: 1, 2, 3, 4, 28, 29, 30, 34, 61, 64, 68, 69, 95, 96, 97; 251162 points over 2663.0 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.705 R☉, Teff = 4629 K, ρ* = 2.08 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 117 ppm, 1h: 93 ppm, 2h: 77 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 19.49 d, semi-amplitude 136 ppm, power 0.03

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 35.61342 | 2240.6492 | 3.11 | 1326 | 65.8 | 25.3 | detected |
| 2 | 7.78981 | 2251.4716 | 2.28 | 215 | 19.9 | 7.8 | detected |
| 3 | 145.68370 | 2304.5204 | 8.25 | 1131 | 45.4 | 9.7 | detected |

Dips at the edges of the data masked before the search (15; depth, duration and S/N): BTJD 1338.516 (1467 ppm, 0.6 h, 10.6); BTJD 1385.964 (934 ppm, 0.7 h, 11.5); BTJD 1394.436 (234 ppm, 9.2 h, 7.7); BTJD 1394.513 (242 ppm, 11.1 h, 7.1); BTJD 1422.516 (3466 ppm, 0.5 h, 7.8); BTJD 2987.811 (528 ppm, 9.2 h, 23.3); BTJD 2987.824 (940 ppm, 4.5 h, 21.5); BTJD 3041.120 (1938 ppm, 0.5 h, 12.9); BTJD 3154.838 (5393 ppm, 1.0 h, 47.7); BTJD 3154.849 (4608 ppm, 1.0 h, 45.5); BTJD 3894.177 (740 ppm, 7.7 h, 19.3); BTJD 3907.032 (594 ppm, 9.2 h, 17.0); BTJD 3936.383 (1423 ppm, 2.1 h, 22.5); BTJD 3936.391 (1266 ppm, 3.7 h, 23.0); BTJD 3950.124 (977 ppm, 1.2 h, 11.0)

Stronger peaks skipped in favor of the signals above:

* iteration 2: P = 287.38666 d, SDE 8.7: only 1 transit(s) with data

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 35.613439 +1.6e-05 / −1.6e-05 |
| T0 (BTJD) | 2240.64827 +0.00043 / −0.00041 |
| Rp/R* | 0.0358 +0.0016 / −0.00099 |
| a/R* | 76.7 +8.9 / −12 |
| b | 0.477 +0.19 / −0.31 |
| T14 (h) | 3.27 +0.057 / −0.043 |
| depth k² (ppm) | 1.28e+03 +1.2e+02 / −70 |
| ρ* (ρ☉) | 4.78 +1.9 / −1.9 |
| Rp (R⊕) | 2.76 +0.28 / −0.26 |

MCMC: 20000 steps, 21 times the longest autocorrelation time (942 steps); 4880 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [note] left out before the fit and the tests, as far from the depth of the other 9 measured transits (median 1444 ppm, scatter 104 ppm): BTJD 1421.540: 2574±105 ppm deep, out-of-transit level +1722 ppm higher before than after
* [pass] odd_even: odd depth 1450±35 ppm vs even 1427±63 ppm: 0.3σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-13±24 ppm, -0.5σ); a 201 ppm dip at phase 0.11 (8.5σ) comes from a single orbit and is not counted
* [pass] shape: U-shaped: ingress+egress = 0.30 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 4.78 ρ☉ vs catalog 2.08 ρ☉ (ratio 2.30, 1.4σ)
* [pass] radius: companion radius 0.25 R_Jup
* [pass] coverage: 8 of 9 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 1.1″ from the target (0.1σ, 4 sectors); stars within 10″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.7897719 +9.9e-06 / −1.4e-05 |
| T0 (BTJD) | 2251.47505 +0.0017 / −0.0014 |
| Rp/R* | 0.0126 +0.0021 / −0.00087 |
| a/R* | 19.6 +3 / −6.3 |
| b | 0.52 +0.3 / −0.35 |
| T14 (h) | 2.64 +0.14 / −0.091 |
| depth k² (ppm) | 158 +58 / −21 |
| ρ* (ρ☉) | 1.66 +0.88 / −1.1 |
| Rp (R⊕) | 0.978 +0.18 / −0.11 |

MCMC: 20000 steps, 17 times the longest autocorrelation time (1150 steps); 4360 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [note] left out before the fit and the tests, as far from the depth of the other 42 measured transits (median 179 ppm, scatter 119 ppm): BTJD 1433.542: 3499±119 ppm deep, out-of-transit level -606 ppm higher before than after; BTJD 1425.752: 807±122 ppm deep, out-of-transit level +1439 ppm higher before than after
* [pass] odd_even: odd depth 253±26 ppm vs even 170±22 ppm: 2.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (25±12 ppm, 2.0σ); a 84 ppm dip at phase 0.37 (6.9σ) comes from a single orbit and is not counted
* [pass] shape: U-shaped: ingress+egress = 0.47 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 1.66 ρ☉ vs catalog 2.08 ρ☉ (ratio 0.80, 0.5σ)
* [pass] radius: companion radius 0.09 R_Jup
* [pass] coverage: 40 of 42 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [n/a] centroid: dip not detected in the target pixels (best S/N 2.3)
* not tested: centroid, so the verdict rests on the other tests

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 145.69616 +0.00048 / −0.00053 |
| T0 (BTJD) | 2304.58799 +0.0036 / −0.0039 |
| Rp/R* | 0.36 +0.38 / −0.21 |
| a/R* | 35.5 +3 / −3.3 |
| b | 1.27 +0.39 / −0.25 |
| T14 (h) | 15.9 +0.73 / −0.55 |
| depth k² (ppm) | 1.3e+05 +4.2e+05 / −1.1e+05 |
| ρ* (ρ☉) | 0.0282 +0.0078 / −0.0072 |
| Rp (R⊕) | 27.5 +29 / −16 |

MCMC: 20000 steps, 10 times the longest autocorrelation time (2003 steps); 1720 samples after burn-in and thinning, acceptance 0.13; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [n/a] odd_even: need at least one odd and one even transit
* [pass] secondary: no significant eclipse at phase 0.5 (18±14 ppm, 1.2σ); a 796 ppm dip at phase 0.91 (34.9σ) comes from a single orbit and is not counted
* [warn] shape: V-shaped: ingress+egress = 0.82 of the duration; posterior P(grazing) = 0.97
* [fail] density: transit-implied ρ* = 0.03 ρ☉ vs catalog 2.08 ρ☉ (ratio 0.01, 11.2σ)
* [pass] radius: companion radius 2.47 R_Jup
* [warn] coverage: 1 of 2 transits with data are fully covered (inside and on both sides): the signal rests on one complete transit
* [n/a] rotation: no clear rotational modulation
* [fail] centroid: the dip is 18.2″ from the target (5.8σ, 1 sector); no cataloged star bright enough to cause it lies there

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
* [centroid_1](centroid_1.png)
* [fit_2](fit_2.png)
* [corner_2](corner_2.png)
* [vetting_2](vetting_2.png)
* [fit_3](fit_3.png)
* [corner_3](corner_3.png)
* [vetting_3](vetting_3.png)
* [centroid_3](centroid_3.png)
