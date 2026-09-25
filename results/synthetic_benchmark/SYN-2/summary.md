# SYN-2 (synthetic)

> **Synthetic light curve** – not a real star.

* Sectors: 1, 2, 3, 4, 5, 6; 114052 points over 164.4 days
* Host star (synthetic star (truth, with 3 % / 5 % radius / mass uncertainties)): R* = 1.1 R☉, Teff = 6000 K, ρ* = 0.826 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 60 ppm, 1h: 47 ppm, 2h: 36 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 17.87 d, semi-amplitude 281 ppm, power 0.66

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 6.27044 | 2083.6120 | 2.92 | 254 | 45.0 | 20.0 | detected |
| 2 | 0.50163 | 2082.1413 | 2.60 | 9 | 5.2 | 6.0 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 6.2700819 +5.1e-05 / −4.8e-05 |
| T0 (BTJD) | 2083.61056 +0.00047 / −0.0004 |
| Rp/R* | 0.0164 +0.0011 / −0.00031 |
| a/R* | 14.5 +0.78 / −3.8 |
| b | 0.336 +0.39 / −0.23 |
| T14 (h) | 3.18 +0.041 / −0.028 |
| depth k² (ppm) | 268 +36 / −10 |
| ρ* (ρ☉) | 1.03 +0.18 / −0.62 |
| Rp (R⊕) | 1.98 +0.12 / −0.079 |

MCMC: 20000 steps, 12 times the longest autocorrelation time (1723 steps); 3320 samples after burn-in and thinning, acceptance 0.21; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 304±8 ppm vs even 322±8 ppm: 1.5σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-4±6 ppm, -0.7σ)
* [pass] shape: U-shaped: ingress+egress = 0.23 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 1.03 ρ☉ vs catalogue 0.83 ρ☉ (ratio 1.25, 0.4σ)
* [pass] radius: companion radius 0.18 R_Jup
* [pass] coverage: 25 of 25 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (17.87 d) or its multiples

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
