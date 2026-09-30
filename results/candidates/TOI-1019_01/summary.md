# TOI-1019.01

* Sectors: 34, 35, 36, 61, 62, 63, 88, 89, 90; 150487 points over 1546.1 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.56 R☉, Teff = 7645 K, ρ* = 0.47 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 460 ppm, 1h: 325 ppm, 2h: 210 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 8.62 d, semi-amplitude 164 ppm, power 0.04

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.23409 | 3012.3284 | 2.90 | 18390 | 682.2 | 28.1 | detected |

Dips at the edges of the data masked before the search (1; depth, duration and S/N): BTJD 2295.235 (16197 ppm, 3.7 h, 80.9)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.2340992 +5.8e-07 / −5.8e-07 |
| T0 (BTJD) | 3012.32772 +6.7e-05 / −6.6e-05 |
| Rp/R* | 0.143 +0.00081 / −0.001 |
| a/R* | 9.75 +0.057 / −0.057 |
| b | 0.711 +0.0054 / −0.0059 |
| T14 (h) | 3.69 +0.011 / −0.01 |
| depth k² (ppm) | 2.06e+04 +2.3e+02 / −2.9e+02 |
| ρ* (ρ☉) | 0.454 +0.008 / −0.0079 |
| Rp (R⊕) | 24.4 +0.77 / −0.76 |

MCMC: 18000 steps, 56 times the longest autocorrelation time (322 steps); 10480 samples after burn-in and thinning, acceptance 0.37; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 20783±57 ppm vs even 20846±59 ppm: 0.8σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (21±31 ppm, 0.7σ)
* [pass] shape: U-shaped: ingress+egress = 0.45 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.45 ρ☉ vs catalogue 0.47 ρ☉ (ratio 0.97, 0.2σ)
* [pass] radius: companion radius 2.18 R_Jup
* [pass] coverage: 39 of 40 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 0.1″ from the target (0.0σ, 4 sectors); stars within 9″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
