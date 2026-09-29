# TOI-592.01

* Sectors: 34; 16827 points over 25.0 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.97 R☉, Teff = 6433 K, ρ* = 0.17 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 341 ppm, 1h: 258 ppm, 2h: 181 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 0.12 d, semi-amplitude 49 ppm, power 0.01

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 10.41218 | 2245.9682 | 3.30 | 1440 | 14.3 | 7.3 | detected |
| 2 | 2.43038 | 2240.4735 | 2.59 | 243 | 6.0 | 4.0 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 0.57151 d, SDE 4.2: folded light curve also brightens (2.9 sigma, against 4.2 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 10.410279 +0.0047 / −0.0065 |
| T0 (BTJD) | 2245.9687 +0.0034 / −0.0054 |
| Rp/R* | 0.0414 +0.003 / −0.0022 |
| a/R* | 18.8 +2.9 / −5 |
| b | 0.497 +0.28 / −0.34 |
| T14 (h) | 3.87 +0.27 / −0.2 |
| depth k² (ppm) | 1.71e+03 +2.6e+02 / −1.8e+02 |
| ρ* (ρ☉) | 0.823 +0.43 / −0.5 |
| Rp (R⊕) | 8.89 +0.76 / −0.63 |

MCMC: 20000 steps, 25 times the longest autocorrelation time (784 steps); 4520 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1877±177 ppm vs even 1710±178 ppm: 0.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (72±85 ppm, 0.8σ)
* [pass] shape: U-shaped: ingress+egress = 0.17 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.82 ρ☉ vs catalogue 0.17 ρ☉ (ratio 4.83, 1.7σ)
* [pass] radius: companion radius 0.79 R_Jup
* [pass] coverage: 2 of 2 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [vetting_1](vetting_1.png)
