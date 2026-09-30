# TOI-1309.01

* Sectors: 40, 41; 33891 points over 55.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 2.13 R☉, Teff = 8807 K, ρ* = 0.228 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 493 ppm, 1h: 359 ppm, 2h: 281 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 0.15 d, semi-amplitude 106 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 1.49917 | 2422.0803 | 3.12 | 1362 | 35.7 | 10.9 | detected |
| 2 | 0.61254 | 2421.7023 | 2.02 | 180 | 7.2 | 7.8 | detected |
| 3 | 0.78089 | 2421.6281 | 1.12 | 214 | 5.1 | 4.8 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 3: P = 0.61261 d, SDE 6.3: folded light curve also brightens (4.6 sigma, against 5.0 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 1.498855 +0.00012 / −0.00012 |
| T0 (BTJD) | 2422.08267 +0.0015 / −0.0014 |
| Rp/R* | 0.201 +0.31 / −0.13 |
| a/R* | 1.52 +0.4 / −0.13 |
| b | 1.13 +0.32 / −0.2 |
| T14 (h) | 5.4 +0.25 / −0.28 |
| depth k² (ppm) | 4.04e+04 +2.2e+05 / −3.6e+04 |
| ρ* (ρ☉) | 0.021 +0.021 / −0.0048 |
| Rp (R⊕) | 46.2 +72 / −30 |

MCMC: 20000 steps, 10 times the longest autocorrelation time (2090 steps); 1720 samples after burn-in and thinning, acceptance 0.13; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 1911±75 ppm vs even 2025±75 ppm: 1.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (8±30 ppm, 0.3σ)
* [warn] shape: V-shaped: ingress+egress = 0.90 of the duration; posterior P(grazing) = 0.85
* [fail] density: transit-implied ρ* = 0.02 ρ☉ vs catalogue 0.23 ρ☉ (ratio 0.09, 5.4σ)
* [fail] radius: companion radius 4.17 R_Jup
* [fail] coverage: 0 of 33 transits with data are fully covered (inside and on both sides): every event lies at the edge of a data segment, where instrumental systematics are common
* [n/a] rotation: no clear rotational modulation
* [fail] centroid: the dip is 37.5″ from the target (14.8σ, 2 sectors), at TIC 287190561 (Tmag 15.0, 36″ from the target), which is bright enough to cause it

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 0.61248056 +0.00023 / −0.00017 |
| T0 (BTJD) | 2421.70146 +0.0041 / −0.0046 |
| Rp/R* | 0.0125 +0.0015 / −0.0014 |
| a/R* | 2.09 +0.37 / −0.43 |
| b | 0.448 +0.33 / −0.31 |
| T14 (h) | 2.1 +0.25 / −0.28 |
| depth k² (ppm) | 157 +40 / −33 |
| ρ* (ρ☉) | 0.326 +0.21 / −0.16 |
| Rp (R⊕) | 2.91 +0.37 / −0.34 |

MCMC: 20000 steps, 51 times the longest autocorrelation time (391 steps); 7760 samples after burn-in and thinning, acceptance 0.30; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 214±53 ppm vs even 279±50 ppm: 0.9σ difference (uncertainties include the 294 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (96±30 ppm, 3.2σ); the phase-0.5 dip comes from a single orbit and is not counted
* [pass] shape: U-shaped: ingress+egress = 0.29 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.33 ρ☉ vs catalogue 0.23 ρ☉ (ratio 1.43, 0.5σ)
* [pass] radius: companion radius 0.26 R_Jup
* [pass] coverage: 53 of 67 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [n/a] centroid: dip not detected in the target pixels (best S/N 1.8)
* not tested: centroid, so the verdict rests on the other tests

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
