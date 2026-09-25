# SYN-1 (synthetic)

> **Synthetic light curve** – not a real star.

* Sectors: 1, 2; 38020 points over 54.8 days
* Host star (synthetic star (truth, with 3 % / 5 % radius / mass uncertainties)): R* = 1.25 R☉, Teff = 6400 K, ρ* = 0.64 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 113 ppm, 1h: 96 ppm, 2h: 82 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 5.07 d, semi-amplitude 450 ppm, power 0.68

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 0.94002 | 2027.6098 | 1.91 | 9465 | 1205.1 | 14.5 | detected |
| 2 | 5.01787 | 2027.0460 | 10.21 | 58 | 5.7 | 4.0 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 0.79099 d, SDE 5.8: folded light curve also brightens (6.0 sigma, against 6.7 sigma for the dip): stellar variability
* iteration 2: P = 0.68434 d, SDE 5.2: folded light curve also brightens (5.7 sigma, against 6.3 sigma for the dip): stellar variability
* iteration 2: P = 1.15401 d, SDE 4.2: folded light curve also brightens (7.4 sigma, against 5.4 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 0.93999979 +8.9e-07 / −8.7e-07 |
| T0 (BTJD) | 2027.61 +1.4e-05 / −1.5e-05 |
| Rp/R* | 0.0953 +0.00019 / −0.00019 |
| a/R* | 3.49 +0.016 / −0.016 |
| b | 0.341 +0.014 / −0.015 |
| T14 (h) | 2.18 +0.0022 / −0.0021 |
| depth k² (ppm) | 9.07e+03 +36 / −36 |
| ρ* (ρ☉) | 0.646 +0.009 / −0.0086 |
| Rp (R⊕) | 13 +0.4 / −0.39 |

MCMC: 20000 steps, 49 times the longest autocorrelation time (411 steps); 15320 samples after burn-in and thinning, acceptance 0.41; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 10624±15 ppm vs even 10612±15 ppm: 0.5σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-2±11 ppm, -0.2σ)
* [pass] shape: U-shaped: ingress+egress = 0.33 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.65 ρ☉ vs catalogue 0.64 ρ☉ (ratio 1.01, 0.1σ)
* [pass] radius: companion radius 1.16 R_Jup
* [pass] coverage: 56 of 56 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (5.07 d) or its multiples

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
