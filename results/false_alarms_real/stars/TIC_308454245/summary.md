# TIC 308454245

* Sectors: 1, 2; 35842 points over 55.2 days
* Host star (TIC v8 (MAST catalogs)): R* = 3.06 R☉, Teff = 10222 K, ρ* = 0.0917 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 138 ppm, 1h: 81 ppm, 2h: 60 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 0.12 d, semi-amplitude 38 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 0.83180 | 1352.9946 | 3.48 | 50 | 8.5 | 7.9 | detected |
| 2 | 0.83095 | 1352.6118 | 4.68 | 47 | 7.9 | 9.6 | same period as #1 (phase 0.54) |
| 3 | 0.91048 | 1352.0890 | 0.59 | 171 | 5.2 | 3.9 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 3: P = 0.66779 d, SDE 7.3: folded light curve also brightens (5.0 sigma, against 6.9 sigma for the dip): stellar variability
* iteration 3: P = 2.66165 d, SDE 4.4: only 0 transit(s) with data
* iteration 3: P = 0.65518 d, SDE 4.4: folded light curve also brightens (3.6 sigma, against 5.4 sigma for the dip): stellar variability
* iteration 3: P = 1.06557 d, SDE 4.3: folded light curve also brightens (3.4 sigma, against 5.3 sigma for the dip): stellar variability
* iteration 3: P = 0.56072 d, SDE 4.2: folded light curve also brightens (3.9 sigma, against 4.9 sigma for the dip): stellar variability
* iteration 3: P = 0.84976 d, SDE 3.9: folded light curve also brightens (3.7 sigma, against 5.2 sigma for the dip): stellar variability
* iteration 3: P = 0.60699 d, SDE 3.9: folded light curve also brightens (4.0 sigma, against 4.7 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 0.8316018 +0.00033 / −0.00033 |
| T0 (BTJD) | 1352.99404 +0.0058 / −0.0065 |
| Rp/R* | 0.00697 +0.00078 / −0.00063 |
| a/R* | 1.62 +0.25 / −0.23 |
| b | 0.407 +0.3 / −0.28 |
| T14 (h) | 3.78 +0.62 / −0.43 |
| depth k² (ppm) | 48.5 +11 / −8.4 |
| ρ* (ρ☉) | 0.0828 +0.045 / −0.03 |
| Rp (R⊕) | 2.33 +0.28 / −0.22 |

MCMC: 20000 steps, 53 times the longest autocorrelation time (377 steps); 7320 samples after burn-in and thinning, acceptance 0.29; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 69±15 ppm vs even 74±15 ppm: 0.2σ difference
* [pass] secondary: eclipse at phase 0.5 (31±9 ppm, 3.7σ) is within the planetary maximum (39 ppm): consistent with a hot planet's occultation
* [pass] shape: intermediate: ingress+egress = 0.79 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.08 ρ☉ vs catalogue 0.09 ρ☉ (ratio 0.90, 0.2σ)
* [pass] radius: companion radius 0.21 R_Jup
* [pass] coverage: 59 of 64 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Signal 2 (not a planet)

**occultation of signal 1 (phase 0.54), consistent with a planet**

* [pass] secondary (of signal 1): eclipse at phase 0.5 (31±9 ppm, 3.7σ) is within the planetary maximum (39 ppm): consistent with a hot planet's occultation

## Figures

* [vetting_1](vetting_1.png)
