# WASP-18

* Sectors: 2, 3, 29, 30, 69, 96, 103, 104, 105, 106; 151163 points over 2906.2 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.35 R☉, Teff = 6226 K, ρ* = 0.491 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 308 ppm, 1h: 279 ppm, 2h: 263 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 0.94 d, semi-amplitude 161 ppm, power 0.07

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 0.94145 | 3204.4118 | 1.91 | 10031 | 789.0 | 41.7 | detected |
| 2 | 0.94145 | 3203.9409 | 2.02 | 401 | 39.0 | 33.5 | same period as #1 (phase 0.50) |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 0.94145237 +1e-08 / −1e-08 |
| T0 (BTJD) | 3204.41181 +1.2e-05 / −1.3e-05 |
| Rp/R* | 0.0989 +0.00013 / −0.00014 |
| a/R* | 3.45 +0.013 / −0.013 |
| b | 0.386 +0.01 / −0.01 |
| T14 (h) | 2.19 +0.0019 / −0.0018 |
| depth k² (ppm) | 9.78e+03 +27 / −27 |
| ρ* (ρ☉) | 0.623 +0.0071 / −0.007 |
| Rp (R⊕) | 14.5 +0.76 / −0.73 |

MCMC: 19000 steps, 162 times the longest autocorrelation time (117 steps); 15000 samples after burn-in and thinning, acceptance 0.43; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 11041±15 ppm vs even 10979±16 ppm: 2.9σ difference
* [pass] secondary: eclipse at phase 0.5 (356±11 ppm, 31.5σ) is within the planetary maximum (1220 ppm): consistent with a hot planet's occultation
* [pass] shape: U-shaped: ingress+egress = 0.26 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.62 ρ☉ vs catalogue 0.49 ρ☉ (ratio 1.27, 1.0σ)
* [pass] radius: companion radius 1.30 R_Jup
* [pass] coverage: 214 of 232 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Signal 2 (not a planet)

**occultation of signal 1 (phase 0.50), consistent with a planet**

* [pass] secondary (of signal 1): eclipse at phase 0.5 (356±11 ppm, 31.5σ) is within the planetary maximum (1220 ppm): consistent with a hot planet's occultation

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
