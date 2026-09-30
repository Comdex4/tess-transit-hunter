# TOI-2140.01

* Sectors: 26; 16650 points over 24.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 1.02 R☉, Teff = 5854 K, ρ* = 1.01 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 519 ppm, 1h: 360 ppm, 2h: 271 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 1.02 d, semi-amplitude 167 ppm, power 0.05

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 2.47075 | 2022.3932 | 1.25 | 12632 | 113.3 | 10.7 | detected |
| 2 | 0.53959 | 2023.3172 | 2.28 | 232 | 5.3 | 5.4 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 2.4706218 +6.3e-05 / −6.6e-05 |
| T0 (BTJD) | 2022.39283 +0.0002 / −0.00019 |
| Rp/R* | 0.128 +0.0033 / −0.0025 |
| a/R* | 8.03 +0.26 / −0.22 |
| b | 0.828 +0.022 / −0.024 |
| T14 (h) | 1.81 +0.035 / −0.03 |
| depth k² (ppm) | 1.63e+04 +8.5e+02 / −6.4e+02 |
| ρ* (ρ☉) | 1.14 +0.11 / −0.091 |
| Rp (R⊕) | 14.2 +0.66 / −0.62 |

MCMC: 20000 steps, 44 times the longest autocorrelation time (454 steps); 8200 samples after burn-in and thinning, acceptance 0.30; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 14944±221 ppm vs even 15011±248 ppm: 0.2σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (73±111 ppm, 0.7σ)
* [pass] shape: intermediate: ingress+egress = 0.60 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 1.14 ρ☉ vs catalogue 1.01 ρ☉ (ratio 1.13, 0.6σ)
* [pass] radius: companion radius 1.26 R_Jup
* [pass] coverage: 9 of 9 transits with data are fully covered (inside and on both sides)
* [n/a] rotation: no clear rotational modulation
* [pass] centroid: the dip is 1.7″ from the target (0.3σ, 1 sector); stars within 9″ of it cannot be excluded, and no catalogued star there is bright enough to cause it

## Figures

* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
