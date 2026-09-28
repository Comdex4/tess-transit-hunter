# TOI-834.01

* Sectors: 11; 13629 points over 23.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.34 R☉, Teff = 5976 K, ρ* = 0.453 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 502 ppm, 1h: 353 ppm, 2h: 267 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 7.88 d, semi-amplitude 454 ppm, power 0.20

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 2.67574 | 1613.0932 | 2.74 | 13242 | 146.8 | 7.9 | detected |
| 2 | 0.61495 | 1609.5193 | 1.34 | 267 | 5.4 | 5.0 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.6755709 +5.8e-05 / −5.7e-05 |
| T0 (BTJD) | 1613.09237 +0.00017 / −0.00017 |
| Rp/R* | 0.113 +0.001 / −0.0009 |
| a/R* | 7.02 +0.11 / −0.19 |
| b | 0.185 +0.12 / −0.12 |
| T14 (h) | 3.21 +0.022 / −0.019 |
| depth k² (ppm) | 1.27e+04 +2.3e+02 / −2e+02 |
| ρ* (ρ☉) | 0.648 +0.03 / −0.052 |
| Rp (R⊕) | 16.5 +0.87 / −0.87 |

MCMC: 20000 steps, 42 times the longest autocorrelation time (474 steps); 7680 samples after burn-in and thinning, acceptance 0.30; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 14234±203 ppm vs even 14697±182 ppm: 1.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (67±103 ppm, 0.7σ)
* [pass] shape: U-shaped: ingress+egress = 0.26 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.65 ρ☉ vs catalogue 0.45 ρ☉ (ratio 1.43, 1.5σ)
* [pass] radius: companion radius 1.47 R_Jup
* [pass] coverage: 6 of 7 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (7.88 d) or its multiples

## Figures

* [vetting_1](vetting_1.png)
