# TOI-1369.01

* Sectors: 56, 57; 36884 points over 56.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.8 R☉, Teff = 9139 K, ρ* = 0.395 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 346 ppm, 1h: 250 ppm, 2h: 182 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 6.46 d, semi-amplitude 97 ppm, power 0.03

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 7.60840 | 2851.9924 | 5.02 | 1293 | 26.0 | 10.5 | detected |
| 2 | 14.30631 | 2852.1398 | 1.54 | 772 | 7.0 | 5.4 | below threshold |

Dips at the edges of the data masked before the search (1; depth, duration and S/N): BTJD 2867.245 (2004 ppm, 9.2 h, 28.4)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 7.6051094 +0.00089 / −0.00075 |
| T0 (BTJD) | 2851.99235 +0.0013 / −0.0012 |
| Rp/R* | 0.0404 +0.001 / −0.00099 |
| a/R* | 10.2 +0.69 / −1.5 |
| b | 0.365 +0.25 / −0.25 |
| T14 (h) | 5.58 +0.13 / −0.095 |
| depth k² (ppm) | 1.63e+03 +85 / −79 |
| ρ* (ρ☉) | 0.244 +0.053 / −0.094 |
| Rp (R⊕) | 7.94 +0.45 / −0.43 |

MCMC: 20000 steps, 23 times the longest autocorrelation time (868 steps); 4760 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 1393±76 ppm vs even 3647±142 ppm: 14.0σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-83±46 ppm, -1.8σ)
* [pass] shape: U-shaped: ingress+egress = 0.11 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 0.24 ρ☉ vs catalogue 0.39 ρ☉ (ratio 0.62, 1.9σ)
* [pass] radius: companion radius 0.71 R_Jup
* [pass] coverage: 4 of 6 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation

## Figures

* [vetting_1](vetting_1.png)
