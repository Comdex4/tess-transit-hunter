# TOI-4597.01

* Sectors: 43, 44; 31833 points over 50.3 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.57 R☉, Teff = 7712 K, ρ* = 0.469 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 1947 ppm, 1h: 823 ppm, 2h: 583 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 1.56 d, semi-amplitude 726 ppm, power 0.07

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 4.66716 | 2499.8666 | 2.43 | 6115 | 39.5 | 12.0 | detected |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 4.6669273 +0.00017 / −0.00018 |
| T0 (BTJD) | 2499.86553 +0.00053 / −0.00054 |
| Rp/R* | 0.0768 +0.0017 / −0.0016 |
| a/R* | 13.5 +0.39 / −0.78 |
| b | 0.227 +0.18 / −0.16 |
| T14 (h) | 2.78 +0.043 / −0.039 |
| depth k² (ppm) | 5.9e+03 +2.6e+02 / −2.5e+02 |
| ρ* (ρ☉) | 1.52 +0.14 / −0.25 |
| Rp (R⊕) | 13.1 +0.48 / −0.47 |

MCMC: 20000 steps, 54 times the longest autocorrelation time (371 steps); 10240 samples after burn-in and thinning, acceptance 0.35; converged (longer than 50 autocorrelation times, estimate stable to 1 %).

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 7624±267 ppm vs even 7568±299 ppm: 0.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (2±192 ppm, 0.0σ)
* [pass] shape: U-shaped: ingress+egress = 0.19 of the duration; posterior P(grazing) = 0.00
* [warn] density: transit-implied ρ* = 1.52 ρ☉ vs catalogue 0.47 ρ☉ (ratio 3.24, 4.7σ)
* [pass] radius: companion radius 1.17 R_Jup
* [pass] coverage: 9 of 9 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
