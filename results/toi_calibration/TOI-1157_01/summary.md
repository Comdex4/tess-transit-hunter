# TOI-1157.01

* Sectors: 40, 41; 37573 points over 55.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 3.59 R☉, Teff = 6017 K, ρ* = 0.024 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 296 ppm, 1h: 247 ppm, 2h: 203 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 4.11 d, semi-amplitude 766 ppm, power 0.26

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 13.07391 | 2420.7502 | 2.02 | 3266 | 34.0 | 11.5 | detected |
| 2 | 12.92578 | 2420.6618 | 13.93 | 335 | 8.1 | 3.5 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 1.00895 d, SDE 4.5: folded light curve also brightens (7.3 sigma, against 10.1 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 13.073705 +0.0006 / −0.00059 |
| T0 (BTJD) | 2420.7492 +0.00072 / −0.00074 |
| Rp/R* | 0.259 +0.36 / −0.15 |
| a/R* | 15.7 +1.5 / −1.2 |
| b | 1.17 +0.38 / −0.19 |
| T14 (h) | 3.1 +0.12 / −0.11 |
| depth k² (ppm) | 6.73e+04 +3.2e+05 / −5.6e+04 |
| ρ* (ρ☉) | 0.302 +0.097 / −0.062 |
| Rp (R⊕) | 101 +1.4e+02 / −60 |

MCMC: 20000 steps, 10 times the longest autocorrelation time (2043 steps); 2160 samples after burn-in and thinning, acceptance 0.15; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 3851±262 ppm vs even 4173±251 ppm: 0.9σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-98±114 ppm, -0.9σ)
* [warn] shape: intermediate: ingress+egress = 0.75 of the duration; posterior P(grazing) = 0.94
* [fail] density: transit-implied ρ* = 0.30 ρ☉ vs catalogue 0.02 ρ☉ (ratio 12.60, 9.0σ)
* [fail] radius: companion radius 9.07 R_Jup
* [pass] coverage: 3 of 4 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (4.11 d) or its multiples

## Figures

* [vetting_1](vetting_1.png)
