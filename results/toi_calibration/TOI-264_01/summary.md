# TOI-264.01

* Sectors: 3, 4; 27598 points over 50.5 days
* Host star (TIC v8 (MAST catalogs)): R* = 2.66 R☉, Teff = 5773 K, ρ* = 0.0547 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 380 ppm, 1h: 294 ppm, 2h: 208 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 1.97 d, semi-amplitude 71 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 2.21663 | 1412.2181 | 3.50 | 3640 | 96.3 | 10.6 | detected |
| 2 | 0.53483 | 1412.5528 | 1.81 | 125 | 5.9 | 4.9 | below threshold |

Dips at the edges of the data masked before the search (1; depth, duration and S/N): BTJD 1396.711 (3384 ppm, 3.1 h, 18.1)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.2167317 +4.9e-05 / −4.9e-05 |
| T0 (BTJD) | 1412.21663 +0.00034 / −0.00033 |
| Rp/R* | 0.065 +0.00089 / −0.00084 |
| a/R* | 3.53 +0.17 / −0.15 |
| b | 0.707 +0.034 / −0.044 |
| T14 (h) | 3.93 +0.041 / −0.041 |
| depth k² (ppm) | 4.22e+03 +1.2e+02 / −1.1e+02 |
| ρ* (ρ☉) | 0.121 +0.018 / −0.015 |
| Rp (R⊕) | 18.9 +0.93 / −0.97 |

MCMC: 20000 steps, 59 times the longest autocorrelation time (337 steps); 10160 samples after burn-in and thinning, acceptance 0.35; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [note] left out before the fit and the tests, as far from the depth of the other 15 measured transits (median 4127 ppm, scatter 226 ppm): BTJD 1394.485: 1998±289 ppm deep, data on one side only
* [pass] odd_even: odd depth 4393±66 ppm vs even 4304±62 ppm: 1.0σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (85±34 ppm, 2.5σ)
* [pass] shape: U-shaped: ingress+egress = 0.26 of the duration; posterior P(grazing) = 0.00
* [warn] density: transit-implied ρ* = 0.12 ρ☉ vs catalog 0.05 ρ☉ (ratio 2.20, 3.3σ)
* [pass] radius: companion radius 1.68 R_Jup
* [pass] coverage: 15 of 15 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 1.0″ from the target (0.1σ, 2 sectors); stars within 9″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
