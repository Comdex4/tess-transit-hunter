# TOI-150.01

* Sectors: 9, 10, 11, 12; 60040 points over 108.4 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.68 R☉, Teff = 5983 K, ρ* = 0.232 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 484 ppm, 1h: 347 ppm, 2h: 253 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 6.30 d, semi-amplitude 145 ppm, power 0.04

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.85702 | 1595.7229 | 5.02 | 5057 | 129.6 | 13.8 | detected |
| 2 | 4.28753 | 1595.0014 | 1.74 | 353 | 6.5 | 5.6 | below threshold |

Dips at the edges of the data masked before the search (2; depth, duration and S/N): BTJD 1571.395 (1697 ppm, 1.2 h, 7.1); BTJD 1595.644 (4727 ppm, 1.2 h, 17.3)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.8574374 +5.9e-05 / −5.9e-05 |
| T0 (BTJD) | 1595.72156 +0.00032 / −0.00032 |
| Rp/R* | 0.0772 +0.00079 / −0.00093 |
| a/R* | 7.39 +0.32 / −0.27 |
| b | 0.468 +0.06 / −0.088 |
| T14 (h) | 5.9 +0.048 / −0.047 |
| depth k² (ppm) | 5.96e+03 +1.2e+02 / −1.4e+02 |
| ρ* (ρ☉) | 0.158 +0.022 / −0.017 |
| Rp (R⊕) | 14.1 +0.65 / −0.65 |

MCMC: 20000 steps, 32 times the longest autocorrelation time (622 steps); 8040 samples after burn-in and thinning, acceptance 0.32; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 6596±97 ppm vs even 6781±97 ppm: 1.3σ difference (uncertainties include the 258 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (42±40 ppm, 1.1σ)
* [pass] shape: U-shaped: ingress+egress = 0.26 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.16 ρ☉ vs catalogue 0.23 ρ☉ (ratio 0.68, 1.6σ)
* [pass] radius: companion radius 1.26 R_Jup
* [pass] coverage: 14 of 14 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [vetting_1](vetting_1.png)
