# TOI-1059.01

* Sectors: 13, 39, 66, 93, 100, 102, 103, 104; 133441 points over 2550.6 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.944 R☉, Teff = 5188 K, ρ* = 1.05 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 506 ppm, 1h: 387 ppm, 2h: 325 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 10.24 d, semi-amplitude 7114 ppm, power 0.34

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 9.44966 | 3852.8614 | 1.42 | 18977 | 237.9 | 35.0 | detected |
| 2 | 78.13588 | 3814.9908 | 1.59 | 7295 | 29.9 | 7.5 | detected |
| 3 | 52.11518 | 3872.3530 | 2.25 | 5606 | 17.7 | 9.5 | detected |

Dips at the edges of the data masked before the search (7; depth, duration and S/N): BTJD 3830.361 (1505 ppm, 9.2 h, 7.7); BTJD 3855.024 (4149 ppm, 3.1 h, 15.0); BTJD 4074.284 (10534 ppm, 1.5 h, 42.7); BTJD 4127.484 (25797 ppm, 0.5 h, 52.9); BTJD 4153.260 (6448 ppm, 3.7 h, 36.6); BTJD 4166.268 (2921 ppm, 0.9 h, 9.2); BTJD 4177.489 (10692 ppm, 0.7 h, 28.4)

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 277.70390 d, SDE 8.8: folded light curve also brightens (62.9 sigma, against 65.3 sigma for the dip): stellar variability
* iteration 2: P = 138.86172 d, SDE 7.6: folded light curve also brightens (62.3 sigma, against 65.9 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 9.4496542 +8.4e-07 / −8.5e-07 |
| T0 (BTJD) | 3852.86089 +9.7e-05 / −9.8e-05 |
| Rp/R* | 0.538 +0.27 / −0.22 |
| a/R* | 25.4 +1.4 / −0.8 |
| b | 1.32 +0.28 / −0.25 |
| T14 (h) | 2.27 +0.033 / −0.034 |
| depth k² (ppm) | 2.89e+05 +3.6e+05 / −1.9e+05 |
| ρ* (ρ☉) | 2.46 +0.43 / −0.22 |
| Rp (R⊕) | 55.1 +27 / −23 |

MCMC: 20000 steps, 13 times the longest autocorrelation time (1482 steps); 2320 samples after burn-in and thinning, acceptance 0.14; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 24609±252 ppm vs even 24467±215 ppm: 0.4σ difference (uncertainties include the 712 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (89±86 ppm, 1.0σ); a 499 ppm dip at phase 0.60 (5.9σ) comes from a single orbit and is not counted
* [warn] shape: intermediate: ingress+egress = 0.79 of the duration; posterior P(grazing) = 1.00
* [warn] density: transit-implied ρ* = 2.46 ρ☉ vs catalogue 1.05 ρ☉ (ratio 2.35, 3.3σ)
* [fail] radius: companion radius 4.94 R_Jup
* [pass] coverage: 19 of 19 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (10.24 d) or its multiples
* [pass] centroid: the dip is 3.1″ from the target (0.7σ, 4 sectors); stars within 9″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 78.135481 +0.00022 / −0.00022 |
| T0 (BTJD) | 3814.98082 +0.0015 / −0.0015 |
| Rp/R* | 0.479 +0.35 / −0.28 |
| a/R* | 143 +16 / −12 |
| b | 1.35 +0.36 / −0.31 |
| T14 (h) | 2.54 +0.18 / −0.18 |
| depth k² (ppm) | 2.3e+05 +4.5e+05 / −1.9e+05 |
| ρ* (ρ☉) | 6.45 +2.4 / −1.5 |
| Rp (R⊕) | 48.8 +36 / −28 |

MCMC: 20000 steps, 24 times the longest autocorrelation time (832 steps); 4200 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 4653±676 ppm vs even 14738±713 ppm: 10.3σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (39±170 ppm, 0.2σ); a 2382 ppm dip at phase 0.31 (6.5σ) comes from a single orbit and is not counted
* [warn] shape: V-shaped: ingress+egress = 1.00 of the duration; posterior P(grazing) = 0.97
* [fail] density: transit-implied ρ* = 6.45 ρ☉ vs catalogue 1.05 ρ☉ (ratio 6.16, 5.1σ)
* [fail] radius: companion radius 4.40 R_Jup
* [warn] coverage: 1 of 2 transits with data are fully covered (inside and on both sides): the signal rests on one complete transit
* [pass] rotation: period is not near the rotation period (10.24 d) or its multiples
* [n/a] centroid: dip not detected in the target pixels (best S/N 1.8)

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 52.106929 +0.0019 / −0.0024 |
| T0 (BTJD) | 3872.3921 +0.013 / −0.0093 |
| Rp/R* | 0.0844 +0.013 / −0.0045 |
| a/R* | 122 +34 / −40 |
| b | 0.637 +0.2 / −0.42 |
| T14 (h) | 2.87 +0.55 / −0.22 |
| depth k² (ppm) | 7.13e+03 +2.4e+03 / −7.5e+02 |
| ρ* (ρ☉) | 9 +9.9 / −6.3 |
| Rp (R⊕) | 8.77 +1.4 / −0.76 |

MCMC: 20000 steps, 17 times the longest autocorrelation time (1209 steps); 3360 samples after burn-in and thinning, acceptance 0.21; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 7743±492 ppm vs even 4028±711 ppm: 4.3σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-317±178 ppm, -1.8σ); a 1179 ppm dip at phase 0.97 (6.5σ) comes from a single orbit and is not counted
* [pass] shape: U-shaped: ingress+egress = 0.31 of the duration; posterior P(grazing) = 0.10
* [pass] density: transit-implied ρ* = 9.00 ρ☉ vs catalogue 1.05 ρ☉ (ratio 8.60, 2.0σ)
* [pass] radius: companion radius 0.78 R_Jup
* [fail] coverage: 0 of 3 transits with data are fully covered (inside and on both sides): every event lies at the edge of a data segment, where instrumental systematics are common
* [pass] rotation: period is not near the rotation period (10.24 d) or its multiples
* [fail] centroid: the dip is 20.1″ from the target (5.0σ, 1 sector); no catalogued star bright enough to cause it lies there

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
