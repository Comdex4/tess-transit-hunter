# TOI-1668.01

* Sectors: 19; 16703 points over 24.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.04 R☉, Teff = 5420 K, ρ* = 0.846 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 333 ppm, 1h: 258 ppm, 2h: 215 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 4.62 d, semi-amplitude 74 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 2.36424 | 1829.8259 | 4.45 | 604 | 15.3 | 7.3 | detected |
| 2 | 8.66567 | 1832.3259 | 1.30 | 1019 | 7.4 | 4.2 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 1.10976 d, SDE 4.6: folded light curve also brightens (4.5 sigma, against 6.7 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.3645812 +0.0012 / −0.0012 |
| T0 (BTJD) | 1829.82585 +0.0031 / −0.0033 |
| Rp/R* | 0.0246 +0.0055 / −0.0017 |
| a/R* | 2.81 +0.25 / −0.55 |
| b | 0.39 +0.32 / −0.27 |
| T14 (h) | 6.23 +0.39 / −0.27 |
| depth k² (ppm) | 607 +3e+02 / −80 |
| ρ* (ρ☉) | 0.0532 +0.016 / −0.026 |
| Rp (R⊕) | 2.81 +0.61 / −0.26 |

MCMC: 20000 steps, 19 times the longest autocorrelation time (1028 steps); 5640 samples after burn-in and thinning, acceptance 0.26; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 893±91 ppm vs even 895±89 ppm: 0.0σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-19±44 ppm, -0.4σ)
* [warn] shape: V-shaped: ingress+egress = 0.88 of the duration; posterior P(grazing) = 0.00
* [fail] density: transit-implied ρ* = 0.05 ρ☉ vs catalogue 0.85 ρ☉ (ratio 0.06, 10.2σ)
* [pass] radius: companion radius 0.25 R_Jup
* [pass] coverage: 9 of 10 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [fail] centroid: the dip is 23.8″ from the target (8.1σ, 1 sector), at TIC 417705686 (Tmag 15.9, 25″ from the target), which is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
