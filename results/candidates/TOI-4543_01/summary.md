# TOI-4543.01

* Sectors: 70, 71; 30831 points over 50.4 days
* Host star (TIC v8 (MAST catalogs)): R* = n/a R☉, Teff = 5047 K, ρ* = n/a ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 297 ppm, 1h: 283 ppm, 2h: 249 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 2.31 d, semi-amplitude 117 ppm, power 0.05

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.77459 | 3235.3465 | 3.47 | 3821 | 46.5 | 10.3 | detected |
| 2 | 0.85944 | 3233.2092 | 3.49 | 134 | 5.0 | 5.0 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.7746126 +7e-05 / −7.3e-05 |
| T0 (BTJD) | 3235.34646 +0.00021 / −0.0002 |
| Rp/R* | 0.0704 +0.0019 / −0.0011 |
| a/R* | 5.65 +0.096 / −0.092 |
| b | 0.886 +0.0055 / −0.0056 |
| T14 (h) | 4.76 +0.029 / −0.028 |
| depth k² (ppm) | 4.96e+03 +2.7e+02 / −1.6e+02 |
| ρ* (ρ☉) | 0.0725 +0.0037 / −0.0035 |
| Rp (R⊕) | – |

MCMC: 20000 steps, 68 times the longest autocorrelation time (296 steps); 10920 samples after burn-in and thinning, acceptance 0.36; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 4276±119 ppm vs even 4486±137 ppm: 1.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-52±80 ppm, -0.6σ)
* [pass] shape: intermediate: ingress+egress = 0.52 of the duration; posterior P(grazing) = 0.00
* [n/a] density: no fitted or catalogue density
* [n/a] radius: no stellar radius
* [pass] coverage: 7 of 8 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

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
