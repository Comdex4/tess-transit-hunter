---
layout: default
title: "Limitations"
kicker: "Read this first"
lede: "What the pipeline does not do, and where its numbers should not be trusted."
---



## What has and has not been run

The [home page](index.md#status-of-the-results) tracks which analyses have been run;
`scripts/update_docs.py` fills in each result from `results/` once its script has run.
The analyses of real TESS data are small samples: five stars with confirmed planets, five
TOI planet candidates, 30 TOIs that the follow-up team has resolved, 100 stars without
known planets, and one light curve for injection–recovery. So:

* **false-alarm rates on real data** come from 100 bright dwarfs observed in two sectors
  ([Validation](validation.md#false-alarms-on-real-stars)). Fainter stars, giants and
  longer baselines, which have more trial periods, have not been measured;
* **vetting thresholds** were checked against 13 recovered planets and 12 recovered false
  positives ([Validation](validation.md#vetting-checked-against-resolved-tois)), too few to
  tune them (see [Vetting](#vetting) below);
* **completeness on real data** comes from injections into one star's light curve.

## Synthetic results are optimistic

The simulator reproduces TESS sampling, stellar variability, correlated noise, and
flagged cadences. It does **not** reproduce the systematics that dominate false alarms in
real data: momentum-dump discontinuities, scattered light near orbit boundaries,
residual pointing jitter, and sector-to-sector calibration offsets. Consequently:

* the noise-only false-alarm rates in [Validation](validation.md) are lower limits;
* the synthetic completeness map in [Completeness](completeness.md) is an upper limit
  for a star with the same white/red-noise level. Real-data completeness has to come from
  injections into real light curves (`scripts/run_injection_recovery.py --tic ...`).

The validation on real stars bears this out. HD 21749's light curve contains a few deep,
isolated dips at the edges of data segments, a kind of event the simulator does not make.
In the first run they hid one of its planets from the search and corrupted a transit of the
other. The search now masks such dips, and a transit whose depth is far from the others' is
left out before the fit ([Validation](validation.md#what-the-real-data-showed)). Of 100 real
stars without known planets, observed for two sectors each, two gave a detection just above
the thresholds. Neither is a transit, and the vetting rejected neither
([Validation](validation.md#false-alarms-on-real-stars)).

## Detection

* **At least two transits.** Single-transit events are never reported; long-period
  planets with one transit in the data are missed by design.
* **Period range.** Periods shorter than 0.5 days are not searched by default
  (`--min-period` lowers the limit).
* **Box model and linear ephemeris.** Planets with large transit-timing variations are
  smeared in the folded light curve and lose S/N.
* **Instrumental dips.** Strong single dips that the data do not cover on both sides are
  masked before each pass, and the SDE is measured only against trial periods that can hold
  two transits ([Search](pipeline/search.md#dips-at-the-edges-of-the-data)). Together they
  let the search find HD 21749 c, which a few such dips had hidden. Dips in the middle of a
  data segment are not masked, and two of them years apart can still pair up into a
  long-period signal that clears both thresholds; the vetting has to reject it. The mask
  cannot tell an instrumental dip from a real transit that falls partly in a gap in the
  data: in the injections into HD 21749's light curve it cost four planets with only two or
  three transits ([Completeness](completeness.md#real-against-synthetic)). Three of those
  four transits were more than a day from the nearest gap longer than half a day, so
  masking only dips next to such gaps would have kept them; whether that would still catch
  the dips that hid HD 21749 c has not been tested.
* **Several planets of similar strength.** Each peak is measured against a periodogram that
  also holds the other planets' peaks. In two sectors of HD 108236, a star with five
  transiting planets, none of them reached SDE 7, so TOI-1233.01 was missed
  ([Validation](validation.md#what-the-resolved-tois-showed)). More data, or a statistic
  that sets the other planets' peaks aside, would help.
* **Red-noise S/N.** The S/N uses a robust (MAD-based) scatter of the flux binned to the
  transit duration. For strongly variable stars, whose detrending residuals are far from
  Gaussian, this can overstate significance. The noise-only calibration in
  [Validation](validation.md#false-alarm-calibration) shows this for the "active" regime. That
  is why a detection also requires a high SDE.
* **Thresholds.** A detection needs SDE ≥ 7, a red-noise S/N above the larger of 7 and
  the trial-corrected 1 % false-alarm level, and at least two transits with data. The
  trial correction assumes Gaussian noise and approximates the number of independent
  trials. It is a guide rather than a guarantee.
* **Spotted stars.** In noise-only simulations of a moderately active star observed for
  three sectors, 11 of 150 light curves gave a false alarm, all but one at the rotation
  period or half of it ([Validation](validation.md#false-alarm-calibration)). The vetting
  flags candidates at those periods but cannot tell them apart from planets; that needs
  independent evidence, such as a clearly planetary transit shape or observations with
  another instrument.
* **Stellar-variability filter.** A peak is skipped when the folded light curve brightens
  with more than 0.65 of the dip's significance. The threshold was chosen from simulations
  (see [Validation](validation.md#lessons-from-building-the-validation)), not calibrated
  on real stars. The test recognises wave-like variability, whose crests are as strong as
  its troughs. Variability with sharp troughs and weak crests can pass it, and then only
  the detection thresholds and the vetting stand in its way. Conversely, a flare that
  survives the outlier clipping adds a brightening at one phase and could, in principle,
  hide a marginal planet. Skipped peaks are listed in every report so that they can be
  inspected.
* **Detrending.** Without a mask, a windowed biweight absorbs roughly a fraction
  T14/window of the depth of a shallow transit (see the tests in `tests/test_detrend.py`).
  The first search iteration runs on unmasked detrending, so long-duration transits
  (evolved hosts, long periods) have reduced search sensitivity. Fitting and
  vetting re-detrend with the transits masked and are not affected. The window can be
  changed with `--window`.
* **Run time.** The number of trial periods grows with the time baseline. Measured grid
  sizes and run times are in [Validation](validation.md#search-cost). The period grid is
  designed to keep multi-year searches tractable (see
  [Methods](methods.md#transit-search-searchpy)), but they still take minutes per
  iteration on a few cores, and longer if the stellar density is unknown.

## Fitting

* **Circular orbits.** Eccentricity is not fitted. An eccentric orbit changes the transit
  duration, which biases a/R* and hence the transit-implied stellar density. The density
  vetting test therefore only fails at factors above 5.
* **Limb darkening** has uninformative (Kipping) priors by default. Gaussian priors from
  model atmospheres can be supplied through `FitConfig.ld_prior`, but no tabulation is
  included.
* **Dilution.** PDCSAP corrects for contaminating flux using TIC-based crowding
  estimates. An unresolved companion star not in the TIC dilutes the transit, so the
  planet radius is underestimated.
* **Stellar parameters** come from the TIC (radius and density, with their catalogue
  uncertainties propagated into the planet radius). Errors in the TIC, for example
  unresolved binaries or evolved stars, propagate directly into planet radii.
* **Convergence.** A chain counts as converged when it is longer than 50 integrated
  autocorrelation times τ and the τ estimate is stable to 1 %. For shallow transits, b,
  a/R*, k, and limb darkening are strongly degenerate and τ is long. In the synthetic
  benchmark no chain met the criterion within the default limit of 20 000 steps: the
  chains spanned 12–49 τ, with the longest τ between about 400 and 1 700 steps. The
  medians and 68 % intervals still matched the injected values (see
  [Validation](validation.md#end-to-end-benchmark-on-synthetic-systems-truth-known)), but
  the tails of the posteriors, grazing solutions in particular, are sampled less
  reliably. Longer chains (`--max-steps`) or limb-darkening priors (`FitConfig.ld_prior`)
  help. Differential-evolution moves were tried on the slowest case and did not mix
  better over long chains. The fits to real data behave the same way: of the 15 in the
  validation, only WASP-18 b's met the criterion (160 τ); the others spanned 8–42 τ. Tests
  that read the posterior inherit its wanderings: for L 98-59's 1.049-day binary, a chain
  that drifted into a grazing solution raised the deepest occultation a planet could produce
  from 9 to 24 ppm, enough for the secondary-eclipse test to pass it
  ([Vetting](pipeline/vet.md#a-real-impostor-the-binary-in-l-98-59s-light-curve)).
  `report.json` and `summary.md` give the chain length in units of τ and flag
  non-converged fits.

## Vetting

* **No pixel-level tests.** The vetting uses only the light curve. It cannot identify a
  background eclipsing binary blended with the target (that needs centroid-offset
  analysis of the target-pixel files and high-resolution imaging). It also cannot test
  whether the signal is on the target star. "Passes all tests" means *consistent with a
  planet*, not *confirmed*.
* **Secondary-eclipse limit.** The maximum planetary occultation depth uses a top-hat
  600–1000 nm approximation of the TESS band and blackbody spectra. That is deliberately
  generous and not a substitute for a physical model.
* **Thresholds** (3σ for odd/even and secondary, 0.8 for the V-shape metric, a factor of 5
  for the density) are conventional choices. Checked against 30 TOIs that the follow-up
  team has resolved, they rejected none of 13 confirmed planets and half of 12 false
  positives ([Validation](validation.md#what-the-resolved-tois-showed)), and no threshold
  change would have done better. That sample is small: it bounds how often real planets
  are rejected only loosely, and it contains no grazing planet.
* **Blends.** The false positives that got through look like planets in every light-curve
  test. Eclipsing binaries on neighbouring stars, blended with the target, look like that,
  and only pixel-level data or follow-up observations can expose them.
* **Tests that cannot run** (the density and radius tests without a stellar radius in the
  TIC) make a verdict "with caveats", never "passes all tests". The verdict then rests on
  the other tests, which is how TOI-1401.01, a false positive with a 2.05 R_J companion,
  earned only a caveat.
* **Averages over transits.** The odd/even, secondary-eclipse and shape tests use the
  folded light curve, so one bad transit could decide them. A transit whose depth is far
  from the others' is therefore left out first, and a dip away from the transit counts only
  if it survives leaving out its strongest orbit. Neither step helps when more than a tenth
  of the transits are affected, or when a bad transit's depth happens to look normal.
  `scripts/transit_timing.py` measures the transits one by one, flags outliers by the same
  rule and shows the odd/even test with and without them.
* **Very high S/N.** With hundreds of transits the statistical errors become so small that
  slight systematic differences between transits approach the 3σ threshold. In the first
  run, WASP-18 b's odd and even depths differed by 0.6 %, at 2.9σ. Measuring each transit
  against the flux around it brought that to 0.8σ, and the uncertainties are never smaller
  than the scatter between transits allows, but a systematic that affects odd and even
  transits differently would still count against a planet.
* **Rotation period.** The rotation test takes the strongest periodicity of the
  un-detrended light curve as the star's rotation, whatever causes it. For WASP-18 it is
  the orbital period itself (161 ppm), most likely the planet's phase curve; it explains
  7 % of the variance, just under the 10 % at which a hot Jupiter would have been warned
  about its own period. For TOI-270 it is 11.39 days, within 0.1 % of planet d's period.
