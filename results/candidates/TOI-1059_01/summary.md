# TOI-1059.01

* Sectors: 13, 39, 66, 93, 100, 102, 103, 104; 133441 points over 2550.6 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.944 R☉, Teff = 5188 K, ρ* = 1.05 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 506 ppm, 1h: 387 ppm, 2h: 325 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 10.24 d, semi-amplitude 7088 ppm, power 0.34

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 9.44966 | 3852.8606 | 1.51 | 18367 | 239.0 | 34.9 | detected |
| 2 | 78.13588 | 3814.9908 | 1.59 | 7302 | 30.0 | 7.6 | detected |
| 3 | 3.15921 | 3850.1302 | 5.28 | 243 | 7.5 | 5.7 | below threshold |

Dips at the edges of the data masked before the search (15; depth, duration and S/N): BTJD 3111.628 (3139 ppm, 1.8 h, 7.7); BTJD 3830.361 (1505 ppm, 9.2 h, 7.7); BTJD 3836.562 (4722 ppm, 0.9 h, 11.3); BTJD 3849.795 (3686 ppm, 5.3 h, 13.2); BTJD 3849.832 (4793 ppm, 3.1 h, 12.5); BTJD 3850.120 (5193 ppm, 0.6 h, 9.9); BTJD 3855.024 (4149 ppm, 3.1 h, 15.1); BTJD 4074.284 (10535 ppm, 1.5 h, 42.3); BTJD 4093.871 (2621 ppm, 2.1 h, 8.1); BTJD 4127.484 (25797 ppm, 0.5 h, 52.9); BTJD 4132.959 (9037 ppm, 0.9 h, 19.9); BTJD 4132.963 (9407 ppm, 0.5 h, 19.3); BTJD 4153.260 (6449 ppm, 3.7 h, 36.6); BTJD 4166.268 (2922 ppm, 0.9 h, 9.2); BTJD 4177.489 (10692 ppm, 0.7 h, 28.4)

Stronger peaks skipped in favour of the signals above:

* iteration 3: P = 52.14481 d, SDE 7.7: folded light curve also brightens (29.1 sigma, against 29.3 sigma for the dip): stellar variability
* iteration 3: P = 32.40271 d, SDE 6.9: folded light curve also brightens (23.4 sigma, against 27.4 sigma for the dip): stellar variability
* iteration 3: P = 45.95347 d, SDE 6.1: folded light curve also brightens (36.1 sigma, against 27.3 sigma for the dip): stellar variability
* iteration 3: P = 70.80300 d, SDE 5.9: folded light curve also brightens (39.1 sigma, against 28.9 sigma for the dip): stellar variability
* iteration 3: P = 78.03805 d, SDE 5.8: folded light curve also brightens (38.0 sigma, against 28.9 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 9.4496542 +8.3e-07 / −8.4e-07 |
| T0 (BTJD) | 3852.86089 +9.2e-05 / −0.0001 |
| Rp/R* | 0.485 +0.34 / −0.19 |
| a/R* | 25.3 +1.6 / −0.74 |
| b | 1.26 +0.35 / −0.23 |
| T14 (h) | 2.27 +0.036 / −0.034 |
| depth k² (ppm) | 2.35e+05 +4.4e+05 / −1.5e+05 |
| ρ* (ρ☉) | 2.45 +0.49 / −0.21 |
| Rp (R⊕) | 49.7 +33 / −20 |

MCMC: 20000 steps, 10 times the longest autocorrelation time (1914 steps); 2240 samples after burn-in and thinning, acceptance 0.15; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 24666±229 ppm vs even 24511±195 ppm: 0.5σ difference (uncertainties include the 646 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (56±88 ppm, 0.6σ); a 476 ppm dip at phase 0.60 (5.6σ) comes from a single orbit and is not counted
* [warn] shape: intermediate: ingress+egress = 0.79 of the duration; posterior P(grazing) = 1.00
* [warn] density: transit-implied ρ* = 2.45 ρ☉ vs catalogue 1.05 ρ☉ (ratio 2.34, 3.0σ)
* [fail] radius: companion radius 4.46 R_Jup
* [pass] coverage: 19 of 19 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (10.24 d) or its multiples

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 78.135522 +0.00021 / −0.00021 |
| T0 (BTJD) | 3814.9809 +0.0014 / −0.0014 |
| Rp/R* | 0.49 +0.34 / −0.26 |
| a/R* | 134 +13 / −11 |
| b | 1.35 +0.35 / −0.28 |
| T14 (h) | 2.79 +0.2 / −0.19 |
| depth k² (ppm) | 2.4e+05 +4.4e+05 / −1.9e+05 |
| ρ* (ρ☉) | 5.31 +1.7 / −1.2 |
| Rp (R⊕) | 50.5 +34 / −27 |

MCMC: 20000 steps, 22 times the longest autocorrelation time (925 steps); 4560 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 5220±726 ppm vs even 14665±687 ppm: 9.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-6±162 ppm, -0.0σ); a 2174 ppm dip at phase 0.31 (6.3σ) comes from a single orbit and is not counted
* [warn] shape: V-shaped: ingress+egress = 0.95 of the duration; posterior P(grazing) = 0.99
* [fail] density: transit-implied ρ* = 5.31 ρ☉ vs catalogue 1.05 ρ☉ (ratio 5.08, 4.5σ)
* [fail] radius: companion radius 4.50 R_Jup
* [fail] coverage: 0 of 2 transits with data are fully covered (inside and on both sides): every event lies at the edge of a data segment, where instrumental systematics are common
* [pass] rotation: period is not near the rotation period (10.24 d) or its multiples

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
