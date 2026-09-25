# TOI-270

* Sectors: 3, 4, 5, 30, 32, 97, 98; 137815 points over 2659.9 days
* Host star (TIC v8 (MAST catalogs)): R* = 0.374 R☉, Teff = 3532 K, ρ* = 6.91 ρ☉
* Scatter of the flattened light curve (robust, binned): 0.5h: 372 ppm, 1h: 269 ppm, 2h: 198 ppm
* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits masked): 11.39 d, semi-amplitude 281 ppm, power 0.12

## Search

| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |
|---|---|---|---|---|---|---|---|
| 1 | 5.66048 | 2187.6298 | 1.50 | 3268 | 89.1 | 42.7 | detected |
| 2 | 11.37971 | 2186.2533 | 1.91 | 2737 | 55.2 | 38.7 | detected |
| 3 | 3.36016 | 2186.8101 | 1.33 | 934 | 31.2 | 37.4 | detected |
| 4 | 56.36665 | 2200.0977 | 3.06 | 1258 | 11.9 | 9.0 | detected |
| 5 | 42.34525 | 2183.9378 | 4.44 | 640 | 9.7 | 6.7 | below threshold |

## Candidate 1

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 5.6604785 +1.1e-06 / −1.2e-06 |
| T0 (BTJD) | 2187.63195 +0.00031 / −0.0003 |
| Rp/R* | 0.0604 +0.0045 / −0.0056 |
| a/R* | 18.5 +3.9 / −2.9 |
| b | 0.682 +0.12 / −0.23 |
| T14 (h) | 1.89 +0.063 / −0.057 |
| depth k² (ppm) | 3.65e+03 +5.6e+02 / −6.4e+02 |
| ρ* (ρ☉) | 2.67 +2.1 / −1.1 |
| Rp (R⊕) | 2.46 +0.2 / −0.22 |

MCMC: 20000 steps, 18 times the longest autocorrelation time (1105 steps); 4040 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (with caveats)**

* [pass] odd_even: odd depth 3966±55 ppm vs even 3959±55 ppm: 0.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (13±38 ppm, 0.3σ)
* [pass] shape: U-shaped: ingress+egress = 0.48 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 2.67 ρ☉ vs catalogue 6.91 ρ☉ (ratio 0.39, 1.8σ)
* [pass] radius: companion radius 0.22 R_Jup
* [pass] coverage: 32 of 35 transits with data are fully covered (inside and on both sides)
* [warn] rotation: period is within 0.6 % of half the rotation period (11.39 d, 281 ppm): residual starspot modulation can mimic a transit there

## Candidate 2

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 11.3797 +4.4e-06 / −4.5e-06 |
| T0 (BTJD) | 2186.25438 +0.00045 / −0.00045 |
| Rp/R* | 0.059 +0.0018 / −0.0015 |
| a/R* | 21.6 +1.8 / −1.6 |
| b | 0.866 +0.025 / −0.032 |
| T14 (h) | 2.46 +0.056 / −0.053 |
| depth k² (ppm) | 3.48e+03 +2.2e+02 / −1.7e+02 |
| ρ* (ρ☉) | 1.04 +0.28 / −0.21 |
| Rp (R⊕) | 2.41 +0.1 / −0.094 |

MCMC: 20000 steps, 46 times the longest autocorrelation time (438 steps); 8040 samples after burn-in and thinning, acceptance 0.31; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [pass] odd_even: odd depth 3104±69 ppm vs even 3144±62 ppm: 0.4σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (-50±50 ppm, -1.0σ)
* [pass] shape: U-shaped: ingress+egress = 0.40 of the duration; posterior P(grazing) = 0.00
* [fail] density: transit-implied ρ* = 1.04 ρ☉ vs catalogue 6.91 ρ☉ (ratio 0.15, 8.0σ)
* [pass] radius: companion radius 0.21 R_Jup
* [pass] coverage: 16 of 17 transits with data are fully covered (inside and on both sides)
* [warn] rotation: period is within 0.1 % of the rotation period (11.39 d, 281 ppm): residual starspot modulation can mimic a transit there

## Candidate 3

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 3.3601629 +8.2e-07 / −9e-07 |
| T0 (BTJD) | 2186.81009 +0.0003 / −0.00029 |
| Rp/R* | 0.0318 +0.00099 / −0.00081 |
| a/R* | 17.1 +2.1 / −3.8 |
| b | 0.477 +0.26 / −0.33 |
| T14 (h) | 1.38 +0.032 / −0.021 |
| depth k² (ppm) | 1.01e+03 +64 / −51 |
| ρ* (ρ☉) | 5.94 +2.4 / −3.1 |
| Rp (R⊕) | 1.3 +0.056 / −0.053 |

MCMC: 20000 steps, 18 times the longest autocorrelation time (1088 steps); 4000 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: planet candidate (passes all tests)**

* [pass] odd_even: odd depth 1063±44 ppm vs even 996±45 ppm: 1.1σ difference
* [pass] secondary: no significant eclipse at phase 0.5 (32±36 ppm, 0.9σ)
* [pass] shape: U-shaped: ingress+egress = 0.18 of the duration; posterior P(grazing) = 0.00
* [pass] density: transit-implied ρ* = 5.94 ρ☉ vs catalogue 6.91 ρ☉ (ratio 0.86, 0.3σ)
* [pass] radius: companion radius 0.12 R_Jup
* [pass] coverage: 50 of 54 transits with data are fully covered (inside and on both sides)
* [pass] rotation: period is not near the rotation period (11.39 d) or its multiples

## Candidate 4

| parameter | posterior median and 68 % interval |
|---|---|
| period (d) | 56.370006 +0.0033 / −0.002 |
| T0 (BTJD) | 2200.12727 +0.023 / −0.016 |
| Rp/R* | 0.0406 +0.0077 / −0.0036 |
| a/R* | 73.5 +25 / −28 |
| b | 0.541 +0.33 / −0.37 |
| T14 (h) | 5.03 +1.3 / −1 |
| depth k² (ppm) | 1.65e+03 +6.8e+02 / −2.8e+02 |
| ρ* (ρ☉) | 1.68 +2.4 / −1.3 |
| Rp (R⊕) | 1.67 +0.31 / −0.17 |

MCMC: 20000 steps, 21 times the longest autocorrelation time (954 steps); 3240 samples after burn-in and thinning, acceptance 0.22; not converged (that needs more than 50 autocorrelation times); treat the posterior tails with caution.

**Vetting verdict: likely false positive**

* [n/a] odd_even: need at least one odd and one even transit
* [pass] secondary: no significant eclipse at phase 0.5 (152±96 ppm, 1.6σ)
* [warn] shape: V-shaped: ingress+egress = 0.99 of the duration; posterior P(grazing) = 0.04
* [pass] density: transit-implied ρ* = 1.68 ρ☉ vs catalogue 6.91 ρ☉ (ratio 0.24, 1.2σ)
* [pass] radius: companion radius 0.15 R_Jup
* [fail] coverage: 0 of 2 transits with data are fully covered (inside and on both sides): every event lies at the edge of a data segment, where instrumental systematics are common
* [pass] rotation: period is not near the rotation period (11.39 d) or its multiples

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
* [fit_2](fit_2.png)
* [corner_2](corner_2.png)
* [vetting_2](vetting_2.png)
* [fit_3](fit_3.png)
* [corner_3](corner_3.png)
* [vetting_3](vetting_3.png)
* [fit_4](fit_4.png)
* [corner_4](corner_4.png)
* [vetting_4](vetting_4.png)
