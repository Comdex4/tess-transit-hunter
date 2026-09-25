# SYN-3 (synthetic)

> **Synthetic light curve** – not a real star.

* Sectors: 1, 2, 3; 57028 points over 82.2 days
* Host star (synthetic star (truth, with 3 % / 5 % radius / mass uncertainties)): R* = 0.38 R☉, Teff = 3500 K, ρ* = 7.11 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 310 ppm, 1h: 232 ppm, 2h: 166 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 15.81 d, semi-amplitude 1843 ppm, power 0.63

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.66001 | 2042.0204 | 1.59 | 3468 | 76.8 | 16.8 | detected |
| 2 | 11.37961 | 2038.7412 | 2.02 | 2604 | 42.9 | 16.0 | detected |
| 3 | 3.36004 | 2041.1212 | 1.33 | 1065 | 27.7 | 21.5 | detected |
| 4 | 0.96532 | 2041.1493 | 0.59 | 165 | 5.4 | 5.5 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.6600254 +5e-05 / −4.9e-05 |
| T0 (BTJD) | 2042.01986 +0.00019 / −0.0002 |
| Rp/R* | 0.0576 +0.0011 / −0.00085 |
| a/R* | 25.8 +0.92 / −2 |
| b | 0.262 +0.2 / −0.18 |
| T14 (h) | 1.72 +0.027 / −0.021 |
| depth k² (ppm) | 3.31e+03 +1.3e+02 / −98 |
| ρ* (ρ☉) | 7.21 +0.8 / −1.6 |
| Rp (R⊕) | 2.39 +0.082 / −0.082 |

MCMC: 20000 steps, 24 times the longest autocorrelation time (838 steps); 5160 samples after burn-in and thinning, acceptance 0.25; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 3984±69 ppm vs even 3860±75 ppm: 1.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-87±53 ppm, -1.6σ)
* [pass] shape: U-shaped: ingress+egress = 0.22 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 7.21 ρ☉ vs catalogue 7.11 ρ☉ (ratio 1.01, 0.1σ)
* [pass] radius: companion radius 0.21 R_Jup
* [pass] coverage: 13 of 13 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (15.81 d) or its multiples

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 11.379804 +0.00021 / −0.00022 |
| T0 (BTJD) | 2038.74016 +0.00045 / −0.00045 |
| Rp/R* | 0.0526 +0.0028 / −0.0022 |
| a/R* | 34 +6 / −6.6 |
| b | 0.569 +0.19 / −0.35 |
| T14 (h) | 2.27 +0.072 / −0.05 |
| depth k² (ppm) | 2.77e+03 +3e+02 / −2.3e+02 |
| ρ* (ρ☉) | 4.06 +2.6 / −1.9 |
| Rp (R⊕) | 2.19 +0.12 / −0.11 |

MCMC: 20000 steps, 17 times the longest autocorrelation time (1149 steps); 4440 samples after burn-in and thinning, acceptance 0.21; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 3114±80 ppm vs even 3011±92 ppm: 0.8σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (28±66 ppm, 0.4σ)
* [pass] shape: U-shaped: ingress+egress = 0.22 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 4.06 ρ☉ vs catalogue 7.11 ρ☉ (ratio 0.57, 1.0σ)
* [pass] radius: companion radius 0.19 R_Jup
* [pass] coverage: 7 of 7 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (15.81 d) or its multiples

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.3599817 +6.3e-05 / −6.7e-05 |
| T0 (BTJD) | 2041.12051 +0.00043 / −0.00048 |
| Rp/R* | 0.0339 +0.0013 / −0.0012 |
| a/R* | 16.9 +1.9 / −3.7 |
| b | 0.478 +0.26 / −0.32 |
| T14 (h) | 1.4 +0.038 / −0.034 |
| depth k² (ppm) | 1.15e+03 +92 / −77 |
| ρ* (ρ☉) | 5.77 +2.2 / −3 |
| Rp (R⊕) | 1.4 +0.071 / −0.063 |

MCMC: 20000 steps, 17 times the longest autocorrelation time (1195 steps); 3800 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1246±58 ppm vs even 1190±57 ppm: 0.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (48±45 ppm, 1.1σ)
* [pass] shape: U-shaped: ingress+egress = 0.17 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 5.77 ρ☉ vs catalogue 7.11 ρ☉ (ratio 0.81, 0.4σ)
* [pass] radius: companion radius 0.13 R_Jup
* [pass] coverage: 21 of 23 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (15.81 d) or its multiples

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [periodogram_2](periodogram_2.png)
* [fold_2](fold_2.png)
* [periodogram_3](periodogram_3.png)
* [fold_3](fold_3.png)
* [periodogram_4](periodogram_4.png)
* [fold_4](fold_4.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
* [fit_2](fit_2.png)
* [corner_2](corner_2.png)
* [vetting_2](vetting_2.png)
* [fit_3](fit_3.png)
* [corner_3](corner_3.png)
* [vetting_3](vetting_3.png)
