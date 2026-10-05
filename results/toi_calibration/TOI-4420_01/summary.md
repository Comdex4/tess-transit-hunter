# TOI-4420.01

* Sectors: 39; 19320 points over 27.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.86 R☉, Teff = 6203 K, ρ* = 0.185 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 342 ppm, 1h: 302 ppm, 2h: 268 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 1.97 d, semi-amplitude 371 ppm, power 0.17

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 4.72578 | 2377.3279 | 2.04 | 5562 | 54.9 | 8.7 | detected |
| 2 | 1.32487 | 2375.7766 | 7.62 | 244 | 6.8 | 5.4 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 4.7260614 +0.00017 / −0.00018 |
| T0 (BTJD) | 2377.32892 +0.00031 / −0.0003 |
| Rp/R* | 0.0829 +0.0021 / −0.0015 |
| a/R* | 8.77 +0.39 / −0.39 |
| b | 0.856 +0.02 / −0.024 |
| T14 (h) | 2.75 +0.041 / −0.038 |
| depth k² (ppm) | 6.88e+03 +3.5e+02 / −2.5e+02 |
| ρ* (ρ☉) | 0.406 +0.056 / −0.051 |
| Rp (R⊕) | 16.9 +0.83 / −0.81 |

MCMC: 20000 steps, 38 times the longest autocorrelation time (529 steps); 6760 samples after burn-in and thinning, acceptance 0.28; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 6254±207 ppm vs even 6462±207 ppm: 0.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (148±119 ppm, 1.2σ)
* [pass] shape: intermediate: ingress+egress = 0.52 of the duration; posterior P(grazing) = 0.00
* [warn] density: transit-implied ρ* = 0.41 ρ☉ vs catalog 0.19 ρ☉ (ratio 2.19, 3.1σ)
* [pass] radius: companion radius 1.50 R_Jup
* [pass] coverage: 6 of 6 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (1.97 d) or its multiples
* [pass] centroid: the dip is 5.7″ from the target (1.7σ, 1 sector); stars within 9″ of it cannot be excluded: TIC 362709882 (Tmag 12.4, 5″) could cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
