# TOI-1476.01

* Sectors: 17; 12842 points over 23.0 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.46 R☉, Teff = 6596 K, ρ* = 0.44 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 640 ppm, 1h: 608 ppm, 2h: 546 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 0.61 d, semi-amplitude 475 ppm, power 0.27

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 1.21734 | 1778.9263 | 2.44 | 6566 | 59.9 | 8.2 | detected |
| 2 | 1.21811 | 1778.3202 | 5.28 | 610 | 10.2 | 6.2 | below threshold |

Dips at the edges of the data masked before the search (1; depth, duration and S/N): BTJD 1772.823 (6541 ppm, 1.5 h, 12.0)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.2175053 +2.5e-05 / −2.6e-05 |
| T0 (BTJD) | 1778.92643 +0.00017 / −0.00017 |
| Rp/R* | 0.0795 +0.00089 / −0.00098 |
| a/R* | 3.37 +0.15 / −0.13 |
| b | 0.426 +0.076 / −0.12 |
| T14 (h) | 2.8 +0.026 / −0.023 |
| depth k² (ppm) | 6.33e+03 +1.4e+02 / −1.6e+02 |
| ρ* (ρ☉) | 0.346 +0.048 / −0.039 |
| Rp (R⊕) | 12.7 +0.65 / −0.65 |

MCMC: 20000 steps, 34 times the longest autocorrelation time (596 steps); 8720 samples after burn-in and thinning, acceptance 0.33; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 6770±158 ppm vs even 6849±160 ppm: 0.4σ difference
* [pass] secondary: eclipse at phase 0.5 (573±89 ppm, 6.4σ) is within the planetary maximum (880 ppm): consistent with a hot planet's occultation
* [pass] shape: U-shaped: ingress+egress = 0.21 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.35 ρ☉ vs catalogue 0.44 ρ☉ (ratio 0.79, 0.9σ)
* [pass] radius: companion radius 1.13 R_Jup
* [pass] coverage: 14 of 15 transits with data are fully covered (inside and on both sides)
* [warn] rotation: period is within 0.1 % of twice it (0.61 d, 475 ppm): residual starspot modulation can mimic a transit there

## Figures

* [vetting_1](vetting_1.png)
