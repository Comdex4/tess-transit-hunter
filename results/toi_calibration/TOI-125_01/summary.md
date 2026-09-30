# TOI-125.01

* Sectors: 1, 2; 36572 points over 56.2 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.852 R☉, Teff = 5280 K, ρ* = 1.47 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 303 ppm, 1h: 211 ppm, 2h: 145 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 6.38 d, semi-amplitude 61 ppm, power 0.02

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 4.65430 | 1355.3566 | 2.60 | 790 | 21.0 | 11.1 | detected |
| 2 | 9.15442 | 1352.7544 | 2.58 | 861 | 16.5 | 11.0 | detected |
| 3 | 19.97780 | 1362.8293 | 2.75 | 856 | 10.6 | 7.8 | detected |
| 4 | 24.20905 | 1349.2869 | 3.72 | 623 | 6.5 | 5.1 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 4.6538002 +0.00037 / −0.00035 |
| T0 (BTJD) | 1355.35511 +0.0011 / −0.0011 |
| Rp/R* | 0.0293 +0.002 / −0.0013 |
| a/R* | 10.8 +1.3 / −2.5 |
| b | 0.483 +0.26 / −0.33 |
| T14 (h) | 3.01 +0.11 / −0.095 |
| depth k² (ppm) | 861 +1.2e+02 / −77 |
| ρ* (ρ☉) | 0.783 +0.33 / −0.42 |
| Rp (R⊕) | 2.73 +0.24 / −0.2 |

MCMC: 20000 steps, 23 times the longest autocorrelation time (868 steps); 4960 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 886±76 ppm vs even 984±74 ppm: 0.9σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-9±48 ppm, -0.2σ)
* [pass] shape: U-shaped: ingress+egress = 0.26 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.78 ρ☉ vs catalogue 1.47 ρ☉ (ratio 0.53, 1.7σ)
* [pass] radius: companion radius 0.24 R_Jup
* [pass] coverage: 11 of 12 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 5.8″ from the target (0.7σ, 1 sector); stars within 17″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 9.150554 +0.00073 / −0.00091 |
| T0 (BTJD) | 1352.75766 +0.0016 / −0.0013 |
| Rp/R* | 0.0302 +0.0019 / −0.0014 |
| a/R* | 22.2 +1.9 / −4.4 |
| b | 0.401 +0.28 / −0.27 |
| T14 (h) | 2.99 +0.1 / −0.083 |
| depth k² (ppm) | 911 +1.2e+02 / −85 |
| ρ* (ρ☉) | 1.76 +0.49 / −0.86 |
| Rp (R⊕) | 2.81 +0.25 / −0.22 |

MCMC: 20000 steps, 25 times the longest autocorrelation time (797 steps); 6400 samples after burn-in and thinning, acceptance 0.27; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 1031±92 ppm vs even 1099±100 ppm: 0.5σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (58±66 ppm, 0.9σ)
* [pass] shape: U-shaped: ingress+egress = 0.33 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 1.76 ρ☉ vs catalogue 1.47 ρ☉ (ratio 1.20, 0.3σ)
* [pass] radius: companion radius 0.25 R_Jup
* [pass] coverage: 6 of 7 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [n/a] centroid: dip not detected in the target pixels (best S/N 3.8)
* not tested: centroid, so the verdict rests on the other tests

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 19.978275 +0.006 / −0.0054 |
| T0 (BTJD) | 1362.82921 +0.0038 / −0.0045 |
| Rp/R* | 0.0318 +0.0032 / −0.0023 |
| a/R* | 43.4 +7.8 / −15 |
| b | 0.528 +0.3 / −0.37 |
| T14 (h) | 3.13 +0.26 / −0.21 |
| depth k² (ppm) | 1.01e+03 +2.1e+02 / −1.4e+02 |
| ρ* (ρ☉) | 2.75 +1.8 / −2 |
| Rp (R⊕) | 2.96 +0.34 / −0.28 |

MCMC: 20000 steps, 23 times the longest autocorrelation time (888 steps); 5720 samples after burn-in and thinning, acceptance 0.25; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 1039±160 ppm vs even 1126±161 ppm: 0.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-21±88 ppm, -0.2σ)
* [pass] shape: U-shaped: ingress+egress = 0.13 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 2.75 ρ☉ vs catalogue 1.47 ρ☉ (ratio 1.87, 0.6σ)
* [pass] radius: companion radius 0.26 R_Jup
* [pass] coverage: 2 of 2 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [n/a] centroid: dip not detected in the target pixels (best S/N 3.1)
* not tested: centroid, so the verdict rests on the other tests

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
