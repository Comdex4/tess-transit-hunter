# TOI-824.01

* Sectors: 11, 12; 33787 points over 54.1 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.73 R☉, Teff = 4488 K, ρ* = 1.8 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 413 ppm, 1h: 309 ppm, 2h: 253 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 14.24 d, semi-amplitude 221 ppm, power 0.09

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 1.39301 | 1627.0655 | 0.98 | 1550 | 29.5 | 17.6 | detected |
| 2 | 13.74373 | 1626.3442 | 2.58 | 809 | 7.7 | 5.3 | below threshold |

Dips at the edges of the data masked before the search (1; depth, duration and S/N): BTJD 1625.546 (752 ppm, 9.2 h, 8.0)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.3930215 +3.7e-05 / −3.8e-05 |
| T0 (BTJD) | 1628.45987 +0.00045 / −0.00044 |
| Rp/R* | 0.0454 +0.0029 / −0.0023 |
| a/R* | 4.47 +0.76 / −0.43 |
| b | 0.895 +0.025 / −0.053 |
| T14 (h) | 1.32 +0.059 / −0.056 |
| depth k² (ppm) | 2.06e+03 +2.7e+02 / −2.1e+02 |
| ρ* (ρ☉) | 0.616 +0.37 / −0.16 |
| Rp (R⊕) | 3.62 +0.37 / −0.34 |

MCMC: 20000 steps, 29 times the longest autocorrelation time (696 steps); 6280 samples after burn-in and thinning, acceptance 0.28; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1706±115 ppm vs even 1735±122 ppm: 0.2σ difference (uncertainties include the 489 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (-87±55 ppm, -1.6σ)
* [pass] shape: U-shaped: ingress+egress = 0.39 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.62 ρ☉ vs catalogue 1.80 ρ☉ (ratio 0.34, 1.7σ)
* [pass] radius: companion radius 0.32 R_Jup
* [pass] coverage: 32 of 34 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 4.9″ from the target (0.9σ, 2 sectors); stars within 12″ of it cannot be excluded: TIC 1133968101 (Tmag 15.7, 8″), TIC 193648234 (Tmag 16.8, 8″) could cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
