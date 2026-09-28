# TOI-619.01

* Sectors: 34, 35; 30527 points over 50.9 days
* Host star (TIC v8 (MAST catalogs)): R* = n/a R☉, Teff = n/a K, ρ* = n/a ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 337 ppm, 1h: 256 ppm, 2h: 207 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 8.78 d, semi-amplitude 187 ppm, power 0.11

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 1.80843 | 2252.2298 | 2.44 | 861 | 25.1 | 11.0 | detected |
| 2 | 0.93378 | 2251.9033 | 2.60 | 111 | 4.7 | 5.0 | below threshold |

Dips at the edges of the data masked before the search (1; depth, duration and S/N): BTJD 2266.394 (1234 ppm, 2.6 h, 8.2)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.808074 +0.00019 / −0.00021 |
| T0 (BTJD) | 2252.23206 +0.0015 / −0.0016 |
| Rp/R* | 0.137 +0.37 / −0.11 |
| a/R* | 1.69 +1.4 / −0.16 |
| b | 1.08 +0.38 / −0.48 |
| T14 (h) | 4.53 +0.25 / −0.56 |
| depth k² (ppm) | 1.88e+04 +2.4e+05 / −1.8e+04 |
| ρ* (ρ☉) | 0.0196 +0.1 / −0.005 |
| Rp (R⊕) | – |

MCMC: 20000 steps, 9 times the longest autocorrelation time (2220 steps); 1640 samples after burn-in and thinning, acceptance 0.12; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 1142±70 ppm vs even 1116±73 ppm: 0.3σ difference (uncertainties include the 252 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (5±29 ppm, 0.2σ)
* [warn] shape: intermediate: ingress+egress = 0.76 of the duration; posterior P(grazing) = 0.76
* [n/a] density: no fitted or catalogue density
* [n/a] radius: no stellar radius
* [pass] coverage: 22 of 25 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (8.78 d) or its multiples
* not tested: density, radius, so the verdict rests on the other tests

## Figures

* [vetting_1](vetting_1.png)
