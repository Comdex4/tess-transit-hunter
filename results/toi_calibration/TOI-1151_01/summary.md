# TOI-1151.01

* Sectors: 14; 11985 points over 26.8 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.62 R☉, Teff = 9032 K, ρ* = 0.539 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 135 ppm, 1h: 101 ppm, 2h: 84 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 13.42 d, semi-amplitude 503 ppm, power 0.55

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 3.47476 | 1694.7364 | 2.92 | 13256 | 342.2 | 8.2 | detected |
| 2 | 1.34318 | 1696.0321 | 1.91 | 113 | 5.1 | 3.8 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.4740737 +3e-05 / −3e-05 |
| T0 (BTJD) | 1694.73667 +6.4e-05 / −6.3e-05 |
| Rp/R* | 0.115 +0.00049 / −0.00049 |
| a/R* | 7.52 +0.069 / −0.065 |
| b | 0.505 +0.016 / −0.017 |
| T14 (h) | 3.53 +0.0089 / −0.0087 |
| depth k² (ppm) | 1.33e+04 +1.1e+02 / −1.1e+02 |
| ρ* (ρ☉) | 0.473 +0.013 / −0.012 |
| Rp (R⊕) | 20.4 +0.56 / −0.56 |

MCMC: 17500 steps, 88 times the longest autocorrelation time (199 steps); 12640 samples after burn-in and thinning, acceptance 0.41; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 14284±64 ppm vs even 14273±65 ppm: 0.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (109±35 ppm, 3.1σ); the phase-0.5 dip comes from a single orbit and is not counted
* [pass] shape: U-shaped: ingress+egress = 0.31 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.47 ρ☉ vs catalog 0.54 ρ☉ (ratio 0.88, 0.8σ)
* [pass] radius: companion radius 1.82 R_Jup
* [pass] coverage: 4 of 4 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (13.42 d) or its multiples
* [pass] centroid: the dip is 2.4″ from the target (0.5σ, 1 sector); stars within 9″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
