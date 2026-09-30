# TOI-1401.01

* Sectors: 23, 24, 25, 26; 65096 points over 104.0 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.43 R☉, Teff = 6403 K, ρ* = n/a ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 1076 ppm, 1h: 1036 ppm, 2h: 1033 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 1.10 d, semi-amplitude 1792 ppm, power 0.73

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 7.38420 | 1986.9589 | 3.47 | 19931 | 70.4 | 12.3 | detected |
| 2 | 7.38504 | 1984.2379 | 3.93 | 1026 | 3.8 | 2.8 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 1.10086 d, SDE 10.9: folded light curve also brightens (53.8 sigma, against 45.0 sigma for the dip): stellar variability
* iteration 2: P = 5.50920 d, SDE 4.9: folded light curve also brightens (27.6 sigma, against 27.9 sigma for the dip): stellar variability
* iteration 2: P = 7.70425 d, SDE 3.9: folded light curve also brightens (26.0 sigma, against 22.2 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.3844874 +4.3e-05 / −4.3e-05 |
| T0 (BTJD) | 1986.95821 +0.00016 / −0.00016 |
| Rp/R* | 0.148 +0.0014 / −0.0011 |
| a/R* | 11 +0.12 / −0.11 |
| b | 0.703 +0.011 / −0.011 |
| T14 (h) | 4.67 +0.025 / −0.025 |
| depth k² (ppm) | 2.18e+04 +4.1e+02 / −3.1e+02 |
| ρ* (ρ☉) | 0.328 +0.011 / −0.01 |
| Rp (R⊕) | 23 +0.21 / −0.17 |

MCMC: 19000 steps, 74 times the longest autocorrelation time (258 steps); 10240 samples after burn-in and thinning, acceptance 0.35; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 22758±650 ppm vs even 22431±673 ppm: 0.3σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (141±344 ppm, 0.4σ)
* [pass] shape: U-shaped: ingress+egress = 0.46 of the duration; posterior P(grazing) = 0.00
* [n/a] density: no fitted or catalogue density
* [pass] radius: companion radius 2.05 R_Jup
* [pass] coverage: 11 of 13 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (1.10 d) or its multiples
* [pass] centroid: the dip is 1.0″ from the target (0.1σ, 4 sectors); stars within 9″ of it cannot be excluded, and no catalogued star there is bright enough to cause it
* not tested: density, so the verdict rests on the other tests

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
