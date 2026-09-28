# TIC 281598203

* Sectors: 1, 2; 36571 points over 56.2 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.34 R☉, Teff = 6239 K, ρ* = n/a ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 215 ppm, 1h: 168 ppm, 2h: 127 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 9.04 d, semi-amplitude 223 ppm, power 0.18

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 1.27199 | 1354.4241 | 7.20 | 90 | 7.7 | 7.8 | detected |
| 2 | 0.63909 | 1352.7733 | 3.49 | 93 | 7.3 | 6.4 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.2669945 +0.00061 / −0.00075 |
| T0 (BTJD) | 1354.45706 +0.0093 / −0.0075 |
| Rp/R* | 0.0115 +0.0005 / −0.00048 |
| a/R* | 1.23 +0.039 / −0.02 |
| b | 0.198 +0.19 / −0.14 |
| T14 (h) | 9.17 +0.32 / −0.42 |
| depth k² (ppm) | 133 +12 / −11 |
| ρ* (ρ☉) | 0.0155 +0.0015 / −0.00075 |
| Rp (R⊕) | 1.69 +0.074 / −0.071 |

MCMC: 20000 steps, 70 times the longest autocorrelation time (284 steps); 7920 samples after burn-in and thinning, acceptance 0.31; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 199±33 ppm vs even 173±34 ppm: 0.6σ difference (uncertainties include the 154 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (-49±15 ppm, -3.3σ)
* [pass] shape: intermediate: ingress+egress = 0.62 of the duration; posterior P(grazing) = 0.00
* [n/a] density: no fitted or catalogue density
* [pass] radius: companion radius 0.15 R_Jup
* [pass] coverage: 37 of 43 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (9.04 d) or its multiples
* not tested: density, so the verdict rests on the other tests

## Figures

* [vetting_1](vetting_1.png)
