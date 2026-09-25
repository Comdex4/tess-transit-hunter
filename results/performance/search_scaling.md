One BLS iteration on noise-only synthetic light curves, 4 worker processes (x86_64, 4 CPUs).

| data | ρ* known | points | trial periods | effective trials | S/N threshold (trial-corrected 1 %) | time per iteration (s) | top noise peak S/N / SDE |
|---|---|---|---|---|---|---|---|
| 1 sector (27 d) | yes | 19010 | 12041 | 2.8e+05 | 7.00 (5.86) | 0.5 | 5.7 / 3.8 |
| 3 sectors (82 d) | yes | 57028 | 42991 | 1.5e+06 | 7.00 (6.14) | 2.3 | 5.9 / 4.9 |
| 13 sectors (356 d) | yes | 247108 | 214269 | 1.3e+07 | 7.00 (6.48) | 24 | 5.6 / 6.9 |
| 26 sectors over 3 years (1086 d) | yes | 494212 | 694018 | 7.1e+07 | 7.00 (6.74) | 125 | 5.8 / 6.1 |
| 26 sectors over 3 years (1086 d) | no | 494212 | 1015247 | 2.2e+08 | 7.00 (6.90) | 540 | 6.0 / 7.7 |

Peaks skipped as stellar variability before the top peak was chosen:

* 1 sector (ρ* known): P = 0.59 d, SDE 4.5: folded light curve also brightens (4.4 sigma, against 4.9 sigma for the dip): stellar variability
* 26 sectors over 3 years (ρ* known): P = 12.03 d, SDE 7.7: folded light curve also brightens (7.0 sigma, against 8.6 sigma for the dip): stellar variability
* 26 sectors over 3 years (ρ* known): P = 0.55 d, SDE 6.9: folded light curve also brightens (4.1 sigma, against 6.0 sigma for the dip): stellar variability
* 26 sectors over 3 years (ρ* unknown): P = 6.01 d, SDE 8.9: folded light curve also brightens (6.3 sigma, against 8.4 sigma for the dip): stellar variability
* 26 sectors over 3 years (ρ* unknown): P = 12.03 d, SDE 7.7: folded light curve also brightens (7.0 sigma, against 8.6 sigma for the dip): stellar variability
