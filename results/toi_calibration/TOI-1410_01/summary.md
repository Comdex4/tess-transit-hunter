# TOI-1410.01

* Sectors: 16; 13909 points over 23.0 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.779 R☉, Teff = 4507 K, ρ* = 1.5 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 328 ppm, 1h: 259 ppm, 2h: 200 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 4.26 d, semi-amplitude 106 ppm, power 0.05

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 1.21700 | 1751.8982 | 1.05 | 1274 | 21.6 | 12.9 | detected |
| 2 | 0.56465 | 1751.7496 | 2.02 | 155 | 5.0 | 4.3 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.2168976 +6.5e-05 / −7.6e-05 |
| T0 (BTJD) | 1751.89815 +0.00039 / −0.00046 |
| Rp/R* | 0.0366 +0.002 / −0.0015 |
| a/R* | 7.74 +0.98 / −1.8 |
| b | 0.479 +0.26 / −0.32 |
| T14 (h) | 1.11 +0.053 / −0.031 |
| depth k² (ppm) | 1.34e+03 +1.5e+02 / −1.1e+02 |
| ρ* (ρ☉) | 4.2 +1.8 / −2.3 |
| Rp (R⊕) | 3.11 +0.3 / −0.28 |

MCMC: 20000 steps, 21 times the longest autocorrelation time (950 steps); 5480 samples after burn-in and thinning, acceptance 0.26; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1441±140 ppm vs even 1528±124 ppm: 0.5σ difference (uncertainties include the 372 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (34±69 ppm, 0.5σ)
* [pass] shape: U-shaped: ingress+egress = 0.09 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 4.20 ρ☉ vs catalogue 1.50 ρ☉ (ratio 2.80, 1.2σ)
* [pass] radius: companion radius 0.28 R_Jup
* [pass] coverage: 16 of 16 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [vetting_1](vetting_1.png)
