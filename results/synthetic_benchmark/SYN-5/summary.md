# SYN-5 (synthetic)

> **Synthetic light curve** – not a real star.

* Sectors: 1, 2; 38020 points over 54.8 days
* Host star (synthetic star (truth, with 3 % / 5 % radius / mass uncertainties)): R* = 1 R☉, Teff = 5800 K, ρ* = 1 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 123 ppm, 1h: 91 ppm, 2h: 70 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 8.06 d, semi-amplitude 703 ppm, power 0.62

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 2.79980 | 2026.2003 | 3.70 | 11785 | 1024.1 | 10.1 | detected |
| 2 | 9.32169 | 2032.0452 | 6.41 | 112 | 5.2 | 4.6 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 1.68813 d, SDE 5.1: folded light curve also brightens (5.0 sigma, against 6.4 sigma for the dip): stellar variability
* iteration 2: P = 8.34599 d, SDE 4.9: folded light curve also brightens (6.4 sigma, against 8.2 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.799979 +2.5e-05 / −2.5e-05 |
| T0 (BTJD) | 2026.20002 +0.00015 / −0.00014 |
| Rp/R* | 0.104 +0.001 / −0.00075 |
| a/R* | 5.47 +0.061 / −0.11 |
| b | 0.162 +0.11 / −0.11 |
| T14 (h) | 4.3 +0.022 / −0.021 |
| depth k² (ppm) | 1.08e+04 +2.1e+02 / −1.6e+02 |
| ρ* (ρ☉) | 0.28 +0.0095 / −0.017 |
| Rp (R⊕) | 11.4 +0.36 / −0.36 |

MCMC: 20000 steps, 40 times the longest autocorrelation time (504 steps); 8240 samples after burn-in and thinning, acceptance 0.31; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 17604±21 ppm vs even 8891±21 ppm: 296.9σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (11±16 ppm, 0.7σ)
* [pass] shape: U-shaped: ingress+egress = 0.28 of the duration; posterior P(grazing) = 0.00
* [warn] density: transit-implied ρ* = 0.28 ρ☉ vs catalogue 1.00 ρ☉ (ratio 0.28, 11.2σ)
* [pass] radius: companion radius 1.01 R_Jup
* [pass] rotation: period is not near the rotation period (8.06 d) or its multiples

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
