# TOI-270

* Sectors: 3, 4, 5, 30, 32, 97, 98; 137815 points over 2659.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.374 R☉, Teff = 3532 K, ρ* = 6.91 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 372 ppm, 1h: 269 ppm, 2h: 198 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 11.39 d, semi-amplitude 279 ppm, power 0.11

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.66048 | 2187.6298 | 1.50 | 3270 | 89.4 | 39.2 | detected |
| 2 | 11.37971 | 2186.2533 | 1.91 | 2738 | 55.3 | 37.1 | detected |
| 3 | 3.36016 | 2186.8101 | 1.33 | 935 | 31.3 | 41.1 | detected |
| 4 | 46.66587 | 2204.2878 | 2.90 | 954 | 9.3 | 7.5 | detected |
| 5 | 88.83541 | 2211.4786 | 4.66 | 530 | 8.2 | 7.6 | detected |

Dips at the edges of the data masked before the search (4; depth, duration and S/N): BTJD 2141.577 (887 ppm, 5.3 h, 10.2); BTJD 2141.652 (688 ppm, 11.1 h, 9.1); BTJD 2200.108 (1438 ppm, 2.6 h, 10.6); BTJD 2200.112 (1308 ppm, 3.7 h, 9.1)

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.660478 +1.2e-06 / −1.2e-06 |
| T0 (BTJD) | 2187.63209 +0.00033 / −0.00031 |
| Rp/R* | 0.0623 +0.0033 / −0.0054 |
| a/R* | 17.1 +3.6 / −2.3 |
| b | 0.746 +0.082 / −0.18 |
| T14 (h) | 1.92 +0.057 / −0.062 |
| depth k² (ppm) | 3.88e+03 +4.2e+02 / −6.4e+02 |
| ρ* (ρ☉) | 2.08 +1.6 / −0.74 |
| Rp (R⊕) | 2.54 +0.16 / −0.22 |

MCMC: 20000 steps, 16 times the longest autocorrelation time (1228 steps); 3920 samples after burn-in and thinning, acceptance 0.24; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 3821±75 ppm vs even 3995±74 ppm: 1.7σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (14±40 ppm, 0.4σ)
* [pass] shape: U-shaped: ingress+egress = 0.47 of the duration; posterior P(grazing) = 0.00
* [warn] density: transit-implied ρ* = 2.08 ρ☉ vs catalog 6.91 ρ☉ (ratio 0.30, 3.3σ)
* [pass] radius: companion radius 0.23 R_Jup
* [pass] coverage: 31 of 35 transits with data are fully covered (inside and on both sides)
* [warn] rotation: period is within 0.6 % of half the rotation period (11.39 d, 279 ppm): residual starspot modulation can mimic a transit there
* [pass] centroid: the dip is 1.8″ from the target (0.3σ, 4 sectors); stars within 9″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 11.3797 +4.5e-06 / −4.4e-06 |
| T0 (BTJD) | 2186.25438 +0.00046 / −0.00046 |
| Rp/R* | 0.059 +0.0019 / −0.0015 |
| a/R* | 21.5 +1.8 / −1.5 |
| b | 0.867 +0.023 / −0.031 |
| T14 (h) | 2.46 +0.054 / −0.052 |
| depth k² (ppm) | 3.48e+03 +2.3e+02 / −1.8e+02 |
| ρ* (ρ☉) | 1.03 +0.28 / −0.2 |
| Rp (R⊕) | 2.41 +0.11 / −0.097 |

MCMC: 20000 steps, 42 times the longest autocorrelation time (472 steps); 8080 samples after burn-in and thinning, acceptance 0.31; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 3142±119 ppm vs even 3205±112 ppm: 0.4σ difference (uncertainties include the 336 ppm scatter between transits)
* [pass] secondary: no significant eclipse at phase 0.5 (-31±53 ppm, -0.6σ)
* [pass] shape: U-shaped: ingress+egress = 0.40 of the duration; posterior P(grazing) = 0.00
* [fail] density: transit-implied ρ* = 1.03 ρ☉ vs catalog 6.91 ρ☉ (ratio 0.15, 18.6σ)
* [pass] radius: companion radius 0.22 R_Jup
* [pass] coverage: 16 of 17 transits with data are fully covered (inside and on both sides)
* [warn] rotation: period is within 0.1 % of the rotation period (11.39 d, 279 ppm): residual starspot modulation can mimic a transit there
* [pass] centroid: the dip is 1.4″ from the target (0.2σ, 4 sectors); stars within 9″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.3601631 +8.4e-07 / −9.9e-07 |
| T0 (BTJD) | 2186.81001 +0.00032 / −0.00033 |
| Rp/R* | 0.0319 +0.001 / −0.0009 |
| a/R* | 16.9 +2.3 / −3.8 |
| b | 0.503 +0.25 / −0.34 |
| T14 (h) | 1.38 +0.032 / −0.022 |
| depth k² (ppm) | 1.02e+03 +66 / −57 |
| ρ* (ρ☉) | 5.7 +2.6 / −3 |
| Rp (R⊕) | 1.3 +0.059 / −0.053 |

MCMC: 20000 steps, 15 times the longest autocorrelation time (1329 steps); 4000 samples after burn-in and thinning, acceptance 0.23; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1036±58 ppm vs even 1068±58 ppm: 0.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (34±35 ppm, 1.0σ)
* [pass] shape: U-shaped: ingress+egress = 0.17 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 5.70 ρ☉ vs catalog 6.91 ρ☉ (ratio 0.83, 0.3σ)
* [pass] radius: companion radius 0.12 R_Jup
* [pass] coverage: 49 of 53 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (11.39 d) or its multiples
* [pass] centroid: the dip is 4.3″ from the target (0.9σ, 4 sectors); stars within 11″ of it cannot be excluded, and no cataloged star there is bright enough to cause it

## Candidate 4

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 46.66692 +0.00026 / −0.00099 |
| T0 (BTJD) | 2204.30353 +0.0061 / −0.016 |
| Rp/R* | 0.0354 +0.0044 / −0.0032 |
| a/R* | 96.4 +16 / −29 |
| b | 0.492 +0.31 / −0.33 |
| T14 (h) | 3.34 +0.33 / −0.23 |
| depth k² (ppm) | 1.26e+03 +3.3e+02 / −2.2e+02 |
| ρ* (ρ☉) | 5.52 +3.2 / −3.7 |
| Rp (R⊕) | 1.45 +0.19 / −0.14 |

MCMC: 20000 steps, 21 times the longest autocorrelation time (958 steps); 3200 samples after burn-in and thinning, acceptance 0.21; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 1253±219 ppm vs even 604±530 ppm: 1.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-19±71 ppm, -0.3σ)
* [pass] shape: U-shaped: ingress+egress = 0.16 of the duration; posterior P(grazing) = 0.03
* [pass] density: transit-implied ρ* = 5.52 ρ☉ vs catalog 6.91 ρ☉ (ratio 0.80, 0.4σ)
* [pass] radius: companion radius 0.13 R_Jup
* [fail] coverage: 0 of 3 transits with data are fully covered (inside and on both sides): every event lies at the edge of a data segment, where instrumental systematics are common
* [pass] rotation: period is not near the rotation period (11.39 d) or its multiples
* [n/a] centroid: dip not detected in the pixels (S/N 2.3); no transit with data inside it and on both sides

## Candidate 5

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 88.837424 +0.00053 / −0.00061 |
| T0 (BTJD) | 2211.47325 +0.0084 / −0.0071 |
| Rp/R* | 0.0288 +0.0049 / −0.0024 |
| a/R* | 82.3 +15 / −28 |
| b | 0.516 +0.32 / −0.35 |
| T14 (h) | 7.35 +0.73 / −0.52 |
| depth k² (ppm) | 827 +3.1e+02 / −1.3e+02 |
| ρ* (ρ☉) | 0.948 +0.61 / −0.68 |
| Rp (R⊕) | 1.18 +0.19 / −0.11 |

MCMC: 20000 steps, 20 times the longest autocorrelation time (1018 steps); 3640 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [fail] odd_even: odd depth 708±107 ppm vs even 1581±167 ppm: 4.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-85±78 ppm, -1.1σ)
* [warn] shape: V-shaped: ingress+egress = 0.89 of the duration; posterior P(grazing) = 0.02
* [fail] density: transit-implied ρ* = 0.95 ρ☉ vs catalog 6.91 ρ☉ (ratio 0.14, 8.0σ)
* [pass] radius: companion radius 0.10 R_Jup
* [warn] coverage: 1 of 3 transits with data are fully covered (inside and on both sides): the signal rests on one complete transit
* [pass] rotation: period is not near the rotation period (11.39 d) or its multiples
* [n/a] centroid: dip not detected in the pixels (S/N 1.5); dip not detected in the pixels (S/N 1.6)

## Figures

* [detrending](detrending.png)
* [search_summary](search_summary.png)
* [periodogram_1](periodogram_1.png)
* [fold_1](fold_1.png)
* [periodogram_2](periodogram_2.png)
* [fold_2](fold_2.png)
* [periodogram_3](periodogram_3.png)
* [fold_3](fold_3.png)
* [periodogram_4](periodogram_4.png)
* [fold_4](fold_4.png)
* [periodogram_5](periodogram_5.png)
* [fold_5](fold_5.png)
* [fit_1](fit_1.png)
* [corner_1](corner_1.png)
* [vetting_1](vetting_1.png)
* [centroid_1](centroid_1.png)
* [fit_2](fit_2.png)
* [corner_2](corner_2.png)
* [vetting_2](vetting_2.png)
* [centroid_2](centroid_2.png)
* [fit_3](fit_3.png)
* [corner_3](corner_3.png)
* [vetting_3](vetting_3.png)
* [centroid_3](centroid_3.png)
* [fit_4](fit_4.png)
* [corner_4](corner_4.png)
* [vetting_4](vetting_4.png)
* [fit_5](fit_5.png)
* [corner_5](corner_5.png)
* [vetting_5](vetting_5.png)
