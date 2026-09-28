# TOI-1108.01

* Sectors: 100, 101, 102, 103; 61684 points over 103.1 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.96 R☉, Teff = 8152 K, ρ* = 0.264 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 1081 ppm, 1h: 579 ppm, 2h: 489 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 2.05 d, semi-amplitude 1362 ppm, power 0.18

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 7.14376 | 4127.3615 | 1.10 | 10102 | 59.5 | 18.4 | detected |
| 2 | 2.04235 | 4124.9356 | 9.61 | 523 | 12.4 | 9.3 | detected |
| 3 | 1.02114 | 4127.4511 | 3.68 | 589 | 16.4 | 10.1 | harmonic of #1 |
| 4 | 2.08769 | 4127.2327 | 6.66 | 583 | 7.7 | 5.9 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 0.52819 d, SDE 9.6: folded light curve also brightens (38.1 sigma, against 42.0 sigma for the dip): stellar variability
* iteration 4: P = 0.55384 d, SDE 6.7: folded light curve also brightens (22.5 sigma, against 29.1 sigma for the dip): stellar variability
* iteration 4: P = 0.52819 d, SDE 6.1: folded light curve also brightens (23.6 sigma, against 28.8 sigma for the dip): stellar variability
* iteration 4: P = 0.59862 d, SDE 6.1: folded light curve also brightens (24.7 sigma, against 26.9 sigma for the dip): stellar variability
* iteration 4: P = 0.56340 d, SDE 6.0: folded light curve also brightens (23.3 sigma, against 26.8 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.1439046 +5e-05 / −5e-05 |
| T0 (BTJD) | 4127.36182 +0.00024 / −0.00025 |
| Rp/R* | 0.455 +0.36 / −0.25 |
| a/R* | 21.5 +1.4 / −1.1 |
| b | 1.29 +0.37 / −0.29 |
| T14 (h) | 1.73 +0.063 / −0.054 |
| depth k² (ppm) | 2.07e+05 +4.5e+05 / −1.6e+05 |
| ρ* (ρ☉) | 2.62 +0.55 / −0.38 |
| Rp (R⊕) | 97 +77 / −53 |

MCMC: 20000 steps, 10 times the longest autocorrelation time (1916 steps); 2280 samples after burn-in and thinning, acceptance 0.16; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 13147±379 ppm vs even 14324±906 ppm: 1.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (79±256 ppm, 0.3σ)
* [warn] shape: intermediate: ingress+egress = 0.79 of the duration; posterior P(grazing) = 0.97
* [fail] density: transit-implied ρ* = 2.62 ρ☉ vs catalogue 0.26 ρ☉ (ratio 9.94, 9.1σ)
* [fail] radius: companion radius 8.69 R_Jup
* [pass] coverage: 6 of 11 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (2.05 d) or its multiples

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.0441432 +0.00014 / −0.00013 |
| T0 (BTJD) | 4125.17285 +0.0074 / −0.0051 |
| Rp/R* | 0.032 +0.0033 / −0.0015 |
| a/R* | 1.57 +0.16 / −0.26 |
| b | 0.55 +0.25 / −0.36 |
| T14 (h) | 10.1 +0.53 / −0.62 |
| depth k² (ppm) | 1.02e+03 +2.2e+02 / −95 |
| ρ* (ρ☉) | 0.0124 +0.0043 / −0.0051 |
| Rp (R⊕) | 6.86 +0.69 / −0.41 |

MCMC: 20000 steps, 17 times the longest autocorrelation time (1212 steps); 4440 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 1135±267 ppm vs even 670±261 ppm: 1.2σ difference (uncertainties include the 1223 ppm scatter between transits)
* [warn] secondary: no eclipse at phase 0.5 (-397±25 ppm, -15.8σ); strongest dip at phase 0.57: 209 ppm (6.9σ)
* [pass] shape: U-shaped: ingress+egress = 0.38 of the duration; posterior P(grazing) = 0.00
* [fail] density: transit-implied ρ* = 0.01 ρ☉ vs catalogue 0.26 ρ☉ (ratio 0.05, 6.7σ)
* [pass] radius: companion radius 0.61 R_Jup
* [pass] coverage: 37 of 43 transits with data are fully covered (inside and on both sides)
* [warn] rotation: period is within 0.4 % of the rotation period (2.05 d, 1362 ppm): residual starspot modulation can mimic a transit there

## Figures

* [vetting_1](vetting_1.png)
