# Archived results

Runs kept because they show why a change to the search was needed. The current results
are in `results/injection_synthetic/`. All three runs use the same injections (same
grid and random seed), so their `injections.csv` files can be compared row by row
using the `index` column.

## `injection_synthetic_before_alias_fix/`

The first full injection–recovery run (`scripts/run_injection_recovery.py --synthetic`),
made with the search code before the commit "Fix search: alias ranking and
stellar-variability rejection". Every injection larger than 3.2 R⊕ that it failed to
recover was detected at half or twice its true period (`match == "alias"`). The SDE
trend was estimated in narrow bins, and a strong transit's own broad periodogram hump
raised the trend at its true period.

## `injection_synthetic_sinusoid_filter_partial/`

The first 1159 injections of a run made with the commit "Make the stellar-variability
filter noise-calibrated", which skipped a BLS peak when the light curve's sinusoid at
its period was much stronger than a box-shaped dip implies. The run was stopped when
the comparison with the first run showed injections lost near the simulated star's
10-day rotation period and its 5-day harmonic. Residual spot modulation at those
periods inflated the sinusoid, so genuine transits were skipped as stellar variability.
The commit "Replace the sinusoid comparison with a folded-brightening test" fixed this.
