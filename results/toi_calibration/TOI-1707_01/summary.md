# TOI-1707.01

* Sectors: 43, 44, 45; 47221 points over 76.5 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.48 R☉, Teff = 6582 K, ρ* = 0.424 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 373 ppm, 1h: 285 ppm, 2h: 214 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 6.48 d, semi-amplitude 164 ppm, power 0.07

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 2.02361 | 2511.1675 | 2.58 | 1309 | 42.3 | 13.5 | detected |
| 2 | 1.17655 | 2511.5890 | 2.76 | 133 | 5.8 | 5.5 | below threshold |

Stronger peaks skipped in favour of the signals above:

* iteration 2: P = 0.70565 d, SDE 7.2: folded light curve also brightens (5.7 sigma, against 6.0 sigma for the dip): stellar variability

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.0238075 +7.8e-05 / −6.5e-05 |
| T0 (BTJD) | 2511.16492 +0.00074 / −0.00082 |
| Rp/R* | 0.0702 +0.11 / −0.017 |
| a/R* | 1.96 +0.24 / −0.13 |
| b | 0.992 +0.14 / −0.048 |
| T14 (h) | 3.77 +0.12 / −0.12 |
| depth k² (ppm) | 4.93e+03 +2.9e+04 / −2.1e+03 |
| ρ* (ρ☉) | 0.0248 +0.01 / −0.0046 |
| Rp (R⊕) | 11.3 +18 / −2.9 |

MCMC: 20000 steps, 9 times the longest autocorrelation time (2126 steps); 2120 samples after burn-in and thinning, acceptance 0.16; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 1718±63 ppm vs even 1737±64 ppm: 0.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-17±30 ppm, -0.6σ)
* [warn] shape: intermediate: ingress+egress = 0.71 of the duration; posterior P(grazing) = 0.84
* [fail] density: transit-implied ρ* = 0.02 ρ☉ vs catalogue 0.42 ρ☉ (ratio 0.06, 7.9σ)
* [pass] radius: companion radius 1.01 R_Jup
* [pass] coverage: 32 of 33 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [vetting_1](vetting_1.png)
