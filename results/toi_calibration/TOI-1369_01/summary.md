# TOI-1369.01

* Sectors: 56, 57; 36884 points over 56.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.8 R☉, Teff = 9139 K, ρ* = 0.395 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 346 ppm, 1h: 250 ppm, 2h: 182 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 6.46 d, semi-amplitude 94 ppm, power 0.03

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 7.60375 | 2851.9924 | 5.36 | 1475 | 33.2 | 10.6 | detected |
| 2 | 14.30631 | 2852.1398 | 1.54 | 772 | 7.0 | 5.5 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.6041578 +0.00054 / −0.00059 |
| T0 (BTJD) | 2851.99108 +0.001 / −0.001 |
| Rp/R* | 0.0434 +0.00091 / −0.00088 |
| a/R* | 10.4 +0.43 / −1.1 |
| b | 0.293 +0.23 / −0.2 |
| T14 (h) | 5.59 +0.091 / −0.064 |
| depth k² (ppm) | 1.88e+03 +80 / −75 |
| ρ* (ρ☉) | 0.263 +0.034 / −0.077 |
| Rp (R⊕) | 8.53 +0.46 / −0.47 |

MCMC: 20000 steps, 27 times the longest autocorrelation time (732 steps); 6560 samples after burn-in and thinning, acceptance 0.29; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 1446±78 ppm vs even 3814±111 ppm: 17.5σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-82±46 ppm, -1.8σ)
* [pass] shape: U-shaped: ingress+egress = 0.10 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.26 ρ☉ vs catalog 0.39 ρ☉ (ratio 0.67, 1.8σ)
* [pass] radius: companion radius 0.76 R_Jup
* [pass] coverage: 4 of 7 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 1.9″ from the target (0.3σ, 2 sectors); stars within 9″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
