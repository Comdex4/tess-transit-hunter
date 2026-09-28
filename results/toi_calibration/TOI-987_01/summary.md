# TOI-987.01

* Sectors: 33; 17454 points over 25.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 2.16 R☉, Teff = 6296 K, ρ* = 0.122 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 384 ppm, 1h: 304 ppm, 2h: 227 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 4.97 d, semi-amplitude 184 ppm, power 0.09

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.21526 | 2215.5730 | 5.02 | 3827 | 63.6 | 8.6 | detected |
| 2 | 0.52987 | 2213.7864 | 3.06 | 119 | 5.6 | 4.3 | below threshold |

Dips at the edges of the data masked before the search (1; depth, duration and S/N): BTJD 2215.590 (2471 ppm, 3.7 h, 16.7)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.2144191 +0.00035 / −0.00036 |
| T0 (BTJD) | 2215.57402 +0.00056 / −0.00057 |
| Rp/R* | 0.0656 +0.0011 / −0.00088 |
| a/R* | 7.38 +0.14 / −0.42 |
| b | 0.181 +0.22 / −0.13 |
| T14 (h) | 5.67 +0.063 / −0.053 |
| depth k² (ppm) | 4.3e+03 +1.4e+02 / −1.1e+02 |
| ρ* (ρ☉) | 0.199 +0.012 / −0.032 |
| Rp (R⊕) | 15.5 +0.73 / −0.73 |

MCMC: 20000 steps, 22 times the longest autocorrelation time (909 steps); 5960 samples after burn-in and thinning, acceptance 0.28; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 4719±112 ppm vs even 4993±112 ppm: 1.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-20±59 ppm, -0.3σ)
* [pass] shape: U-shaped: ingress+egress = 0.27 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.20 ρ☉ vs catalogue 0.12 ρ☉ (ratio 1.63, 1.9σ)
* [pass] radius: companion radius 1.38 R_Jup
* [pass] coverage: 4 of 4 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [vetting_1](vetting_1.png)
