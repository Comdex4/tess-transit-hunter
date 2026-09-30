# pi Men

* Sectors: 1, 4, 8, 11, 12, 13, 27, 28, 31, 34, 38, 39, 61, 62, 64, 65, 66, 67, 68, 88, 89, 93, 94, 95; 393006 points over 2581.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.15 R☉, Teff = 5992 K, ρ* = 0.725 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 47 ppm, 1h: 36 ppm, 2h: 27 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 9.58 d, semi-amplitude 15 ppm, power 0.01

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 6.26781 | 2391.0347 | 2.92 | 253 | 106.5 | 52.2 | detected |
| 2 | 21.11098 | 2379.9146 | 5.27 | 32 | 10.4 | 6.5 | below threshold |

Dips at the edges of the data masked before the search (17; depth, duration and S/N): BTJD 1410.941 (381 ppm, 1.0 h, 7.7); BTJD 1410.942 (371 ppm, 1.5 h, 7.3); BTJD 1421.281 (970 ppm, 0.5 h, 13.4); BTJD 1422.233 (261 ppm, 7.7 h, 9.5); BTJD 1535.024 (1603 ppm, 0.9 h, 32.4); BTJD 1638.921 (145 ppm, 5.3 h, 9.6); BTJD 2085.615 (265 ppm, 0.5 h, 7.4); BTJD 2987.715 (67 ppm, 9.2 h, 7.5); BTJD 3067.959 (220 ppm, 2.6 h, 9.3); BTJD 3097.682 (149 ppm, 9.2 h, 9.3); BTJD 3097.706 (183 ppm, 5.3 h, 8.4); BTJD 3154.958 (199 ppm, 11.1 h, 26.2); BTJD 3179.572 (380 ppm, 0.6 h, 9.4); BTJD 3179.581 (347 ppm, 1.0 h, 9.8); BTJD 3894.177 (181 ppm, 7.7 h, 14.9); BTJD 3907.046 (560 ppm, 0.9 h, 16.4); BTJD 3907.052 (669 ppm, 0.5 h, 15.7)

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 253.28643 d, SDE 12.6: folded light curve also brightens (46.2 sigma, against 42.3 sigma for the dip): stellar variability
* iteration 2: P = 172.76855 d, SDE 11.5: folded light curve also brightens (56.6 sigma, against 38.3 sigma for the dip): stellar variability
* iteration 2: P = 506.61423 d, SDE 11.0: folded light curve also brightens (87.5 sigma, against 41.1 sigma for the dip): stellar variability
* iteration 2: P = 518.31434 d, SDE 10.5: folded light curve also brightens (83.3 sigma, against 39.1 sigma for the dip): stellar variability
* iteration 2: P = 148.21835 d, SDE 8.7: folded light curve also brightens (48.7 sigma, against 34.5 sigma for the dip): stellar variability
* iteration 2: P = 124.50788 d, SDE 8.2: folded light curve also brightens (39.4 sigma, against 29.6 sigma for the dip): stellar variability
* iteration 2: P = 151.95717 d, SDE 8.1: folded light curve also brightens (45.3 sigma, against 33.6 sigma for the dip): stellar variability
* iteration 2: P = 168.88645 d, SDE 6.8: folded light curve also brightens (88.3 sigma, against 33.0 sigma for the dip): stellar variability
* iteration 2: P = 338.80547 d, SDE 6.2: only 1 transit(s) with data
* iteration 2: P = 217.08293 d, SDE 6.8: folded light curve also brightens (57.8 sigma, against 34.0 sigma for the dip): stellar variability
* iteration 2: P = 335.11112 d, SDE 6.2: only 1 transit(s) with data
* iteration 2: P = 296.43638 d, SDE 6.8: folded light curve also brightens (87.9 sigma, against 33.6 sigma for the dip): stellar variability
* iteration 2: P = 237.15393 d, SDE 6.5: folded light curve also brightens (43.2 sigma, against 32.9 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 6.2678219 +9.9e-07 / −1e-06 |
| T0 (BTJD) | 2384.76648 +0.00014 / −0.00015 |
| Rp/R* | 0.0166 +0.00031 / −0.00016 |
| a/R* | 15.6 +0.71 / −1.6 |
| b | 0.313 +0.22 / −0.21 |
| T14 (h) | 2.98 +0.012 / −0.011 |
| depth k² (ppm) | 274 +10 / −5.3 |
| ρ* (ρ☉) | 1.28 +0.18 / −0.37 |
| Rp (R⊕) | 2.08 +0.084 / −0.086 |

MCMC: 20000 steps, 18 times the longest autocorrelation time (1121 steps); 5400 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [note] left out before the fit and the tests, as far from the depth of the other 90 measured transits (median 303 ppm, scatter 36 ppm): BTJD 3136.905: 104±38 ppm deep, out-of-transit level -364 ppm higher before than after
* [pass] odd_even: odd depth 309±5 ppm vs even 311±5 ppm: 0.3σ difference (uncertainties include the 32 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (1±3 ppm, 0.4σ)
* [pass] shape: U-shaped: ingress+egress = 0.22 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 1.28 ρ☉ vs catalogue 0.73 ρ☉ (ratio 1.77, 1.5σ)
* [pass] radius: companion radius 0.19 R_Jup
* [pass] coverage: 89 of 90 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 9.8″ from the target (0.1σ, 1 sector); stars within 87″ of it cannot be excluded: TIC 261139071 (Tmag 14.0, 33″) could cause it

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
* [centroid_1](centroid_1.png)
