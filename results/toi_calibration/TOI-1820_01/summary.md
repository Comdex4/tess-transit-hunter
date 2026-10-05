# TOI-1820.01

* Sectors: 49; 13493 points over 24.2 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.4 R☉, Teff = 5778 K, ρ* = 0.377 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 338 ppm, 1h: 244 ppm, 2h: 180 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 12.10 d, semi-amplitude 114 ppm, power 0.05

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 4.86281 | 2651.6099 | 2.29 | 5155 | 67.4 | 8.6 | detected |
| 2 | 1.20367 | 2649.9208 | 4.45 | 144 | 5.0 | 4.2 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 4.8606716 +0.00036 / −0.00036 |
| T0 (BTJD) | 2651.6071 +0.00056 / −0.00056 |
| Rp/R* | 0.0799 +0.0026 / −0.002 |
| a/R* | 7.96 +0.43 / −0.35 |
| b | 0.863 +0.016 / −0.022 |
| T14 (h) | 3.05 +0.074 / −0.068 |
| depth k² (ppm) | 6.39e+03 +4.1e+02 / −3.2e+02 |
| ρ* (ρ☉) | 0.287 +0.048 / −0.036 |
| Rp (R⊕) | 12.2 +0.69 / −0.64 |

MCMC: 20000 steps, 51 times the longest autocorrelation time (389 steps); 8920 samples after burn-in and thinning, acceptance 0.32; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 5889±164 ppm vs even 5947±164 ppm: 0.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-59±88 ppm, -0.7σ)
* [pass] shape: U-shaped: ingress+egress = 0.49 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.29 ρ☉ vs catalog 0.38 ρ☉ (ratio 0.76, 1.1σ)
* [pass] radius: companion radius 1.09 R_Jup
* [pass] coverage: 4 of 4 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 1.3″ from the target (0.2σ, 1 sector); stars within 9″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
