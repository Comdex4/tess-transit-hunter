# WASP-18

* Sectors: 2, 3, 29, 30, 69, 96, 103, 104, 105, 106; 151163 points over 2906.2 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.35 R☉, Teff = 6226 K, ρ* = 0.491 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 308 ppm, 1h: 279 ppm, 2h: 263 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 0.94 d, semi-amplitude 161 ppm, power 0.07

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 0.94145 | 3204.4118 | 1.91 | 10062 | 787.8 | 40.2 | detected |
| 2 | 0.94145 | 3203.9409 | 2.02 | 399 | 38.9 | 31.9 | same period as #1 (phase 0.50) |

Dips at the edges of the data masked before the search (7; depth, duration and S/N): BTJD 1368.612 (5260 ppm, 0.5 h, 16.2); BTJD 1406.210 (9731 ppm, 0.5 h, 29.3); BTJD 2127.369 (6060 ppm, 0.7 h, 19.8); BTJD 2130.234 (7568 ppm, 0.7 h, 24.7); BTJD 4166.583 (7008 ppm, 1.0 h, 27.5); BTJD 4177.393 (2087 ppm, 0.5 h, 7.6); BTJD 4235.330 (9241 ppm, 0.5 h, 31.6)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 0.94145237 +9.9e-09 / −9.8e-09 |
| T0 (BTJD) | 3204.41182 +1.2e-05 / −1.2e-05 |
| Rp/R* | 0.0991 +0.00013 / −0.00013 |
| a/R* | 3.45 +0.013 / −0.012 |
| b | 0.388 +0.0095 / −0.01 |
| T14 (h) | 2.19 +0.0018 / −0.0018 |
| depth k² (ppm) | 9.82e+03 +27 / −26 |
| ρ* (ρ☉) | 0.622 +0.0068 / −0.0066 |
| Rp (R⊕) | 14.5 +0.75 / −0.75 |

MCMC: 14000 steps, 126 times the longest autocorrelation time (111 steps); 11480 samples after burn-in and thinning, acceptance 0.43; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (passes all tests)**

* [note] left out before the fit and the tests, as far from the depth of the other 221 measured transits (median 10558 ppm, scatter 248 ppm): BTJD 3188.407: 8079±327 ppm deep, data on one side only
* [pass] odd_even: odd depth 10808±19 ppm vs even 10783±21 ppm: 0.9σ difference
* [pass] secondary: eclipse at phase 0.5 (355±11 ppm, 31.4σ) is within the planetary maximum (1227 ppm): consistent with a hot planet's occultation
* [pass] shape: U-shaped: ingress+egress = 0.26 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.62 ρ☉ vs catalogue 0.49 ρ☉ (ratio 1.26, 1.0σ)
* [pass] radius: companion radius 1.30 R_Jup
* [pass] coverage: 214 of 225 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Signal 2 (not a planet)

**occultation of signal 1 (phase 0.50), consistent with a planet**

* [pass] secondary (of signal 1): eclipse at phase 0.5 (355±11 ppm, 31.4σ) is within the planetary maximum (1227 ppm): consistent with a hot planet's occultation

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
