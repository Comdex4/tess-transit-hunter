---
layout: default
title: "Methods reference"
kicker: "Reference"
lede: "Every processing step and default in one place, with citations. For the illustrated walk-through, start with the pipeline pages."
---



This page describes what the pipeline does at each step and why. Every choice listed here
is a default of the code (`src/transit_hunter/`); all of them can be changed through the
configuration dataclasses or the command-line interface.

## Data: SPOC 2-minute PDCSAP photometry (`data.py`)

* **Source.** All TESS light curves produced by the Science Processing Operations Center
  (SPOC) at 120-s cadence for the requested TIC ID, found and downloaded with
  `lightkurve.search_lightcurve(..., author="SPOC", exptime=120)`.
* **Flux.** `PDCSAP_FLUX`. Presearch Data Conditioning removes common-mode systematics
  with cotrending basis vectors and corrects for contaminating flux from neighbouring
  stars (`CROWDSAP`) and for target flux outside the aperture (`FLFRCSAP`), so transit
  depths can be compared directly with physical depths.
* **Quality mask.** Cadences with any of the "default" QUALITY bits are removed: attitude
  tweak, safe mode, coarse point, Earth point, Argabrightening, reaction-wheel
  desaturation, manual exclude, impulsive outlier, and bad calibration (the same
  definition as lightkurve's default bitmask; a test checks that they agree). Cadences
  with non-finite time, flux, or uncertainty are removed.
* **Normalisation.** Each sector is divided by its median flux.
* **Outliers.** A running median (0.5-day window, computed per contiguous segment) gives
  a local trend; points more than 4 robust standard deviations (1.4826 × MAD) *above* it
  are removed, iterating until the set of flagged points no longer changes. Points
  *below* the trend are not clipped by default: a transit is a run of consecutive low
  points, and a symmetric clip would delete deep transits. The test-suite demonstrates
  that a symmetric clip removes most in-transit points of a 1 % transit, while the
  asymmetric clip removes none.
* **Cache.** The raw FITS files are kept in lightkurve's download cache and the cleaned,
  stitched light curve is stored as a compressed `.npz` file (with provenance metadata:
  per-sector bookkeeping, cleaning configuration, software versions) keyed by a hash of
  the cleaning configuration. Later runs never touch the network.

## Detrending (`detrend.py`)

Stellar variability and residual instrumental trends are removed with a
**time-windowed Tukey biweight** filter (`wotan`). In the comparison of Hippke et al.
(2019, AJ 158, 143) the biweight was the most reliable detrender for transit searches: it
follows rotational modulation but treats the few in-transit points in each window as
outliers. The default window is **0.75 days** (configurable); the light curve is split at
gaps longer than 0.5 days and each segment is detrended separately.

A windowed filter still absorbs part of a *shallow* transit: when the in-transit points
are not far enough below the rest of the window to be down-weighted, the local trend dips
by roughly the transit depth times T14/window. The pipeline therefore detrends twice:

1. without a mask, for the search;
2. with every detected transit **masked** (a window two transit durations wide) for fitting
   and vetting. Masked points are excluded from the window estimates, so the trend under a
   transit is determined by the neighbouring out-of-transit data.

The synthetic tests quantify both effects (see `tests/test_detrend.py`).

## Transit search (`search.py`)

**Box Least Squares** (Kovács, Zucker & Mazeh 2002; astropy implementation, log-likelihood
objective) is run on the flattened light curve.

*Period grid.* Trial periods run from 0.5 days to half the time baseline (so at least two
transits can be in the data). If the trial frequency is off by δf, successive transits
drift in phase, and over a baseline B the folded transit is smeared by B·P·δf. Requiring
the smear to stay below D/OS for a transit of duration D gives a grid uniform in
ln(frequency) with step

    δ ln f = D_min / (OS · B),    OS = 3

(cf. Ofir 2014). The period range is split into logarithmic bands (8 per decade). Each
band tests only durations that are physically possible there: for a circular orbit the
central-transit duration is T ≈ (P/π)·asin(R*/a) with a/R* = (Gρ*P²/3π)^(1/3), so bounds
on the stellar density ρ* bound the duration at each period. The shortest duration is
0.3× the central duration for the densest allowed star (an impact parameter of about
0.95; one extra grid step is allowed below it), and the longest is 1.2× the central duration
for the least dense allowed star (the factor covers 1 + Rp/R*). With
no stellar information the density range is 0.05–60 ρ☉; when the TIC density of the host
is known (the usual case), densities within a factor of 3 of it are used. Long-period
bands therefore get longer minimum durations, coarser phase bins, and far fewer trial
periods, which keeps multi-year baselines tractable. Trial durations form a geometric
grid from 0.5 to 12 hours in which consecutive durations differ by 20 %.

*Binning.* The search runs on 10-minute bins (coarser, up to 1 hour, in bands whose
shortest duration allows it). The best peak is then **refined on the unbinned data**
with a fine local grid in period and duration.

*Detection statistics.* From the log-likelihood periodogram we form the S/N-like spectrum
√(2 ΔlogL), subtract its slow rise with period, and standardise it. The rise comes from
noise peaks growing with period because more phases are tried. The trend is the median in
bins of equal width in log-period (20 per decade, about 12 % wide), interpolated. Equal
width matters: a strong transit raises the spectrum over a broad range of nearby trial
periods, because subsets of its transits still line up. A narrow bin around the true period
would take that hump for the trend, depress the signal's own SDE, and hand the peak to its
P/2 alias. The Signal Detection Efficiency is SDE = (peak − mean)/std. The trend, mean
and standard deviation are taken only from trial periods whose best box holds at least two
transits with data (the condition a detection must meet), and then applied to every trial.
In a light curve spread thinly over years, the best box at most long trial periods covers
one dip, with the other transits in gaps. Those trials can never be detections, but their
large scatter would otherwise set the scale against which every signal is measured.
Periods below which two stretches of data (or one stretch twice) hold a whole box at every
phase are counted as eligible without checking; above it, each trial's transits are
counted on a cadence-wide grid of the data.

We also compute a **red-noise-aware S/N**: σ_D, the robust scatter of the out-of-transit
flux averaged in bins of one transit duration, gives a depth uncertainty σ_D/√N_transits
(Pont, Zucker & Queloz 2006). Because σ_D includes correlated noise, this S/N is lower than
the white-noise S/N for active or noisy stars.

*Dips at the edges of the data.* Before each pass, single dips are found by averaging the
flux in boxes of every trial duration centred every quarter-duration: a box whose average
lies at least **7 times** its uncertainty below the median is a dip. The uncertainty is the
robust scatter of such averages in the same sector (which includes red noise), scaled up
for a box that is missing cadences. A dip that the data do not cover inside (75 % of the
cadences) and on both sides (half of a one-duration flank each), the vetting's coverage
criterion, and that lies within **1.5 of its durations, or 6 hours** if that is longer, of
the start or end of a data segment (segments split at gaps longer than half a day), is
masked over two of its durations, like a detected transit. Such dips at the edges of data
segments are the most common instrumental events in TESS light curves. Every trial period
can place its box on a strong one, which raises the whole periodogram, and two of them years
apart can pair into a long-period "planet". A dip left uncovered only by a few missing
cadences inside a segment is kept: in the validation light curves most such dips were
transits of the planets themselves. A real transit lost at the edge of a segment is one the
vetting would not count either. The masked dips are listed in the report, and the fit and
vetting use the light curve without them.

*Choosing the peak.* Peaks are examined in order of decreasing SDE, among trials whose best
box holds at least two transits with data. For each one:

1. **Harmonic family.** The periods P/3, P/2, 2P, and 3P are checked, and the search moves
   to the one with clearly (≥ 1.2×) higher raw log-likelihood. For a genuine transit the
   likelihood is highest at the true period, since folding at P/2 or 2P mixes in empty or
   missing transits.
2. **Transit coverage.** At least two transits must contain data.
3. **Stellar variability.** Detrending leaves a small coherent residual of starspot
   modulation, and a box fitted to one of its troughs can stack into a significant peak at
   (or near) the rotation period. A transiting body only removes light, whereas the trough
   of a wave comes with crests. The light curve is therefore folded at the peak's period
   and averaged in a box of the peak's duration at every phase (in steps of a fifth of the
   duration). Each box average is compared with the median of all of them, in units of its
   white-noise uncertainty. The peak is skipped as stellar variability if the strongest
   *brightening*, at least two durations from the dip, is more than **0.65 times** as
   significant as the dip itself. This is a variant of the Kepler Robovetter's model-shift
   uniqueness test (Coughlin et al. 2016) that ignores other dips, so that the secondary
   eclipses of eclipsing binaries do not count against them (the vetting stage deals with
   those). Boxes next to the dip are excluded because unmasked detrending leaves small
   positive "shoulders" around a transit. For a transit in white noise the strongest
   brightening is a noise fluctuation of about √(2 ln(P/D)) σ, typically 2.5–3σ and well
   under half of a 7σ dip. For a pure sinusoid the ratio is 1. Unrelated variability at the orbital period adds bumps
   too, but a transit detected at S/N ≥ 7 still stands well above them. Skipped peaks and
   the reason are listed in the report.

The first peak that passes is refined on the unbinned data.

A peak is a **detection** if

* SDE ≥ 7,
* red-noise S/N ≥ max(7, √(2 ln(N/α))), and
* at least two transits contain data. Single-transit peaks at long periods, common in
  gapped multi-year data, are skipped in favour of the next-highest peak.

The second term in the S/N threshold is a **trial correction**. N is the approximate
number of statistically independent (period, phase, duration) combinations searched: at
duration D, a band of periods contains (B/D)·ln(P_hi/P_lo) independent frequencies, each with
P/D independent phases, and durations are counted once per factor of two. α = 1 % is the
tolerated false-alarm probability per light curve for Gaussian noise. Long multi-sector
searches try many more combinations, so their threshold rises. The floor of 7 is comparable
to the multiple-event-statistic threshold of the SPOC pipeline. Both thresholds are checked against
noise-only simulations (see [Validation](validation.md#false-alarm-calibration)).

*Iterative search.* After a detection, the **raw** light curve is detrended again with the
transits of every signal found so far masked (a mask two durations wide), the masked points
are removed, and BLS is run again. This continues until a peak fails the thresholds or five
signals have been found. Re-detrending matters: an unmasked windowed trend dips under every
transit and leaves small coherent "shoulders" around it, which can fold constructively at
subharmonics P/n of a real planet.

A new signal is classified against the earlier ones:

* **Harmonic.** Its period is within 0.2 % of an integer multiple or fraction (≤ 10) of an
  earlier period, *and* its transits coincide in time with the earlier ephemeris. It is
  masked but not counted as a planet. Both conditions are needed because real systems are
  often close to, but not in, resonance (TOI-270 c and d are near a 2:1 period ratio), and
  such planets must not be merged.
* **Another eclipse of the same orbit.** Its period equals an earlier signal's, or P/2 or P/3
  of it, within 0.2 %. None of its transits that contain data overlaps an earlier transit,
  and all of them sit at one phase of the earlier period. Once the earlier transits are
  masked, a secondary eclipse at phase 0.5 folds equally well at P/2, which is why unit
  fractions are included. Two planets sharing an orbit are practically unknown, so the
  signal is recorded as the *other eclipse* of the earlier one. That is a secondary eclipse
  of an eclipsing binary, or a hot planet's occultation, and the vetting of the earlier
  signal decides which (below). This check runs before the harmonic check.

## Transit fitting (`fit.py`)

A circular-orbit **batman** model (Kreidberg 2015) with quadratic limb darkening, times a
constant baseline, is fitted with the affine-invariant ensemble sampler **emcee**
(Foreman-Mackey et al. 2013) to data within ±2.5 BLS durations of each transit.
Transits of the other detected planets are removed first.

| parameter | prior |
|---|---|
| mid-transit time T0 (epoch nearest the data centre) | uniform, ±1 BLS duration |
| period P | uniform, ±(duration × P / time span) around the BLS period |
| radius ratio k = Rp/R* | uniform (10⁻⁴, 1) |
| ln(a/R*) | uniform (ln 1.2, ln 500) |
| impact parameter b | uniform (0, 1 + k) |
| limb darkening q1, q2 (Kipping 2013) | uniform (0, 1); optional Gaussian prior on (u1, u2) |
| baseline f0 | uniform (0.9, 1.1) |
| ln σ_jitter | uniform (ln 10⁻⁷, ln 0.1) |

The Kipping parameterisation, u1 = 2√q1·q2 and u2 = √q1·(1 − 2q2), samples exactly the
physically allowed quadratic laws (intensity positive and decreasing towards the limb)
with uniform priors. Tabulated coefficients, for example from stellar-atmosphere models
for the star's Teff and log g, can be imposed as Gaussian priors on (u1, u2) through
`FitConfig.ld_prior`.

The **stellar density is deliberately not a prior**. Comparing the density implied by
the transit shape with the catalogue value is one of the vetting tests.

*Sampling.* 40 walkers start in a small ball around the maximum-a-posteriori point, found
with Powell's method from three impact parameters (0.1, 0.5, 0.8) to avoid the
grazing/non-grazing local optima, and move with emcee's default stretch move. The chain
runs until it is longer than 50 integrated autocorrelation times and the autocorrelation
estimate has changed by less than 1 % (checked every 500 steps; at least 2 000 and at most
20 000 steps). Burn-in is 2τ and the chain is thinned by τ/2. Each report gives the chain
length in units of the longest autocorrelation time and flags chains that stopped at the
step limit as not converged. For shallow transits that is the usual outcome: b, a/R*, k,
and the limb-darkening coefficients are strongly degenerate, and in the synthetic benchmark
the longest autocorrelation times ranged from about 400 to 1 700 steps (see
[Limitations](limitations.md#fitting)).

*Derived quantities* are computed sample by sample: inclination, T14 and T23, geometric
depth k², mean stellar density ρ* = 3π(a/R*)³/(GP²), and — using the TIC stellar radius,
whose uncertainty is propagated by drawing R* from a normal distribution truncated at
zero — the planet radius Rp = k·R*, the semi-major axis, and the equilibrium temperature
T_eq = Teff·√(R*/2a) (zero albedo, full heat redistribution). Reported values are
posterior medians with the 15.9–84.1 percentile (68 %) interval.

## Vetting (`vet.py`)

These tests look for the signatures of eclipsing binaries (EBs). Uncertainties are
inflated by a red-noise factor β, the ratio of the scatter of binned out-of-transit data
to its white-noise expectation.

*Single bad transits.* Before the fit and the tests, every transit with data inside it
and on at least one side is measured on its own: its depth is the median of the flanks
(0.75–2 durations from mid-transit, on the sides that have data) minus the median of the
central 70 % of the transit. With at least six transits measured, a transit whose depth
is more than **5 times** the scatter from the median is left out; the scatter is the larger
of the depths' robust spread and their typical uncertainty. Outliers must be rare: if more
than a tenth of the transits (and more than one) stand out, none is dropped, which protects
the two alternating depth groups of an eclipsing binary found at half its period. Dropped
transits are listed in the vetting reasons.

* **Odd/even depths.** An EB with two similar eclipses is found by BLS at half its true
  period, so odd and even "transits" are different eclipses. The amplitude of the fitted
  transit shape is estimated separately for odd and even epochs (linear least squares),
  each transit measured against its own reference level: the median of the
  out-of-transit points within 1.5 durations of it, whose uncertainty is included. When
  each parity has at least three transits, each parity's uncertainty is raised, if needed,
  to the robust scatter of single-transit amplitudes about their parity's median divided
  by √N, so that ordinary transit-to-transit variation is not read as an odd/even
  difference at high S/N. A difference of more than **3σ** fails.
* **Secondary eclipse at phase 0.5.** The flux deficit in a box one transit duration wide
  at phase 0.5 is compared with its flanks. A significant (≥3σ) secondary fails only if it
  is more than **twice the largest plausible planetary occultation**: reflected light with
  geometric albedo 1, (Rp/a)², plus thermal emission from a zero-albedo dayside without
  heat redistribution (T_day = Teff·√(R*/a)·(2/3)^¼) radiating as a blackbody in the
  600–1000 nm TESS band. Hot Jupiters such as WASP-18 b do show real occultations, and
  this criterion keeps them from being mistaken for EBs. For eccentric orbits, a box is
  also scanned across all phases. A dip of ≥5σ (stricter, because many phases are tried)
  that is deeper than the same limit also fails. A dip, at phase 0.5 or in the scan, counts
  only if its S/N stays at the threshold when the orbit contributing most to it is left
  out; a single instrumental dip does not repeat, and is reported but not counted. Without
  an MCMC fit, Rp/R* and a/R* for the limit are estimated from the BLS depth and duration.
  Any *same-period* signal found by the search is left in the data during this test, so the
  test sees it.
* **V- versus U-shape.** A trapezoid is fitted to the folded transit and the metric is
  the fraction of the duration spent in ingress and egress: 0 for a box and 1 for a "V".
  The posterior probability of grazing geometry, P(b + k > 1), is also reported. A value
  ≥ 0.8 or P(grazing) > 0.5 is a **warning**, not a failure, because grazing planets
  exist.
* **Stellar density.** The transit-implied ρ* is compared with the catalogue density in
  log space. A catalogue value with no uncertainty is assigned 25 %. The significance is
  the posterior probability that the transit-implied density lies at or beyond the
  catalogue value, with the catalogue's uncertainty folded in, converted to Gaussian
  standard deviations. For a log-normal posterior that is the difference over the combined
  width; unlike that ratio, it is not diluted when the posterior has two modes, as when a
  fit wanders between a grazing and a non-grazing solution. A difference larger
  than **3σ** gives a warning; one that is also larger than
  a **factor of 5** fails. Eccentric orbits alone can produce factors of a few, since
  ρ_circ/ρ_true = [(1 + e sin ω)/√(1 − e²)]³.
* **Radius** (supplementary). A companion larger than 2.5 R_Jup is not a planet.
* **Coverage.** A transit counts as fully covered if data exist for at least 75 % of its
  duration and for half of a one-duration flank on each side. Dips right at the start or
  end of a data segment (after a gap, at an orbit or sector boundary) are common
  instrumental artefacts, and pairing two of them across a long gap can produce a
  plausible-looking "planet". A signal with no fully covered transit fails; one with a
  single fully covered transit gets a warning.
* **Rotation period** (warning only). The strongest periodicity of the un-detrended light
  curve (Lomb–Scargle periodogram of 30-minute bins, with the transits of all detected
  signals masked) is taken as the rotation period if a sinusoid at it explains at least
  10 % of the variance. A candidate within 5 % of half, once, or twice that period gets a
  warning. Residual spot modulation concentrates the search's false alarms at those
  periods (see [Validation](validation.md#false-alarm-calibration)), but planets can orbit
  there too. SPOC's PDC step can suppress variability on timescales longer than about ten
  days, so long rotation periods may be missed.
* **Centroid** (`centroid.py`, `pixels.py`; real stars only). Where in the target-pixel
  file the flux drops. For every transit that the tests above use, the difference image
  is each pixel's median over the flanks (0.75–2 durations, the two sides averaged) minus
  its median over the central 70 % of the transit. The difference images of a sector are
  averaged; the per-pixel noise is the cadence-to-cadence scatter carried through the
  medians, scaled by one factor from the transits' own scatter about their mean (from
  difference images at other phases, away from the transit and phase 0.5, when there are
  fewer than four transits). The TESS pixel response function (PRF) from the MAST
  calibration files, interpolated to the target's CCD position between the four nearest of
  the 5 × 5 models per CCD, plus a constant, is fitted by least squares within 4 pixels of
  the target, with a non-negative amplitude, starting from the target, the most significant
  pixel and every TIC star within 2.5′ bright enough to cause the dip; the lowest χ² wins.
  The position's covariance is the larger of the fit's (scaled by the reduced χ² if above
  1) and the covariance of 50 fits to transits resampled with replacement. Sectors whose
  fitted amplitude has S/N below **4** are not used. Each sector's position becomes an
  offset (east, north) from the TIC position of the target, propagated with its proper
  motion from epoch J2000 to the sector's mid-time; up to **four** sectors, those with the
  most in-transit data, are averaged with inverse-covariance weights, and a systematic
  floor of **2.5″** is added to each axis. The offset's squared Mahalanobis distance, a
  chi-square with two degrees of freedom, is converted to a Gaussian-equivalent
  significance; **3σ** fails. The report names the nearest TIC star to the dip whose flux
  ratio to the target is at least the transit depth (bright enough to cause the dip when
  totally eclipsed), and lists such stars that the offset does not exclude.

A same-period signal is reported as the other eclipse of its candidate. It is labelled a
*secondary eclipse of an eclipsing binary* if that candidate's secondary test failed, or an
*occultation* consistent with a planet if it passed.

Any failed test gives the verdict **"likely false positive"**. Warnings, or a test that
could not run, give **"planet candidate (with caveats)"**; the untested checks are named in
the reasons. The rotation test is the exception: no rotational modulation means there is
no rotation period to coincide with. Otherwise the verdict is **"planet candidate (passes
all tests)"**. The centroid test resolves blended EBs only down to a few arcseconds from
the target (its 3σ limit is about 9″ at best); closer ones need high-resolution imaging,
which is outside this project. For simulated light curves, which have no pixels, the
centroid test is not run.

## Injection–recovery (`inject.py`)

Transits are drawn on a period × radius grid (log-uniform within each cell; impact
parameter uniform in [0, 0.9]; epoch uniform within the first period; circular orbits
around the host's mass and radius). They are multiplied into the light curve **before
detrending**, so any damage detrending does to transits is included. Each injected light
curve then goes through the same detrend and iterative search as a real target (up to two
iterations). An injection is **recovered** if a detected signal has a period within 1 %
of the injection and a mid-transit time within half an injected duration of an injected
transit. Detections at 1/2, 2, 1/3, or 3 times the period that line up in time are
recorded as aliases and not counted. Injections run in parallel, one process per core,
and results are appended to a CSV as they finish, so runs can be resumed.

## References

* Coughlin J. L. et al. 2016, ApJS 224, 12 (Kepler Robovetter, model-shift uniqueness test)
* Hippke M., David T. J., Mulders G. D., Heller R. 2019, AJ 158, 143 (wotan)
* Kipping D. M. 2010, MNRAS 408, 1758 (supersampling); 2013, MNRAS 435, 2152 (limb darkening)
* Kovács G., Zucker S., Mazeh T. 2002, A&A 391, 369 (BLS)
* Kreidberg L. 2015, PASP 127, 1161 (batman)
* Foreman-Mackey D. et al. 2013, PASP 125, 306 (emcee)
* Ofir A. 2014, A&A 561, A138 (optimal period sampling)
* Pont F., Zucker S., Queloz D. 2006, MNRAS 373, 231 (red noise)
* Seager S., Mallén-Ornelas G. 2003, ApJ 585, 1038 (stellar density from transits)
* Stassun K. G. et al. 2019, AJ 158, 138 (TIC v8)
* Winn J. N. 2010, "Transits and Occultations", arXiv:1001.2010
