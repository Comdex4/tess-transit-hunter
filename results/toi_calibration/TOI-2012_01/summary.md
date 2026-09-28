# TOI-2012.01

* Sectors: 24; 14733 points over 26.5 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.6 R☉, Teff = 5981 K, ρ* = 0.269 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 446 ppm, 1h: 343 ppm, 2h: 247 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 10.08 d, semi-amplitude 312 ppm, power 0.14

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 3.05669 | 1968.1428 | 3.74 | 7477 | 138.6 | 7.3 | detected |
| 2 | 0.69706 | 1969.6522 | 0.74 | 339 | 5.1 | 4.0 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.056548 +0.0001 / −0.00011 |
| T0 (BTJD) | 1968.1432 +0.00029 / −0.00029 |
| Rp/R* | 0.0859 +0.00063 / −0.00063 |
| a/R* | 6.01 +0.054 / −0.1 |
| b | 0.107 +0.11 / −0.076 |
| T14 (h) | 4.22 +0.029 / −0.025 |
| depth k² (ppm) | 7.38e+03 +1.1e+02 / −1.1e+02 |
| ρ* (ρ☉) | 0.311 +0.0085 / −0.016 |
| Rp (R⊕) | 15 +0.72 / −0.69 |

MCMC: 20000 steps, 64 times the longest autocorrelation time (310 steps); 9320 samples after burn-in and thinning, acceptance 0.33; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 8504±149 ppm vs even 8307±98 ppm: 1.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (138±65 ppm, 2.1σ)
* [pass] shape: U-shaped: ingress+egress = 0.18 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.31 ρ☉ vs catalogue 0.27 ρ☉ (ratio 1.16, 0.7σ)
* [pass] radius: companion radius 1.34 R_Jup
* [pass] coverage: 6 of 7 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (10.08 d) or its multiples

## Figures

* [vetting_1](vetting_1.png)
