# TOI-600.01

* Sectors: 34, 35; 30776 points over 51.0 days
* Host star (TIC v8 (MAST catalogs)): R* = n/a R☉, Teff = n/a K, ρ* = n/a ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 338 ppm, 1h: 242 ppm, 2h: 183 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 8.23 d, semi-amplitude 76 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 4.36599 | 2251.4917 | 2.02 | 665 | 12.5 | 11.5 | detected |
| 2 | 0.77409 | 2252.0390 | 2.44 | 108 | 4.9 | 5.0 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 4.3659641 +0.00046 / −0.00056 |
| T0 (BTJD) | 2251.49027 +0.0018 / −0.0029 |
| Rp/R* | 0.0269 +0.0078 / −0.0026 |
| a/R* | 13.2 +2.4 / −5.5 |
| b | 0.51 +0.37 / −0.35 |
| T14 (h) | 2.24 +0.29 / −0.15 |
| depth k² (ppm) | 723 +4.8e+02 / −1.3e+02 |
| ρ* (ρ☉) | 1.63 +1 / −1.3 |
| Rp (R⊕) | – |

MCMC: 20000 steps, 14 times the longest autocorrelation time (1456 steps); 3640 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 934±110 ppm vs even 828±121 ppm: 0.6σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (39±61 ppm, 0.6σ)
* [warn] shape: V-shaped: ingress+egress = 0.82 of the duration; posterior P(grazing) = 0.08
* [n/a] density: no fitted or catalog density
* [n/a] radius: no stellar radius
* [pass] coverage: 11 of 11 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [fail] centroid: the dip is 26.8″ from the target (9.4σ, 2 sectors), at TIC 134333591 (Tmag 15.0, 27″ from the target), which is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
