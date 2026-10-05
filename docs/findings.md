---
layout: default
title: "Findings"
kicker: "Results of the batch searches"
lede: "Six years of TESS data searched for planets around M dwarfs: one strong candidate, one weak lead, and a reason for every other signal."
---

## How the search was run

Each TESS year was searched on its own with the [batch search](batch.md), from sector 1 to
sector 83 (2018–24). For each year it took up to 1,000 M dwarfs (T<sub>eff</sub> ≤ 3,900 K,
TESS magnitude ≤ 13) with 2-minute light curves in at least two of that year's sectors, ran
the full pipeline with quick MCMC fits, and screened the survivors. The screening listed 62
signals for review, and each was then checked by hand: against catalogs of known eclipsing
binaries, in the star's raw light curve for rotation and short-period variation, in the
target pixels, and above all in the star's light curves from its other TESS years. A real
planet transits in every year at the same period and depth; noise and instrumental events do
not. That last check is now a script, `scripts/check_other_years.py`.

<div class="note note--info" markdown="1">
<span class="note__t">Where these numbers come from</span>
Unlike the rest of this site, the tables of outcomes below are written by hand from those
checks. Every number about G 249-11, and its two figures, come from
[`results/g249-11`]({{ site.github_url }}/tree/main/results/g249-11), with the command
that reproduces each.
</div>

## G 249-11 (TIC 417732194): a candidate super-Earth

One signal holds up: a 5.307-day transit on G 249-11, an M4.5 dwarf 29 parsecs away. The
batch found it in sectors 59 and 60 (2022–23). Searched on their own, the light curves from
2019 (sector 19) and 2023–24 (sectors 73 and 86) find the same period.

<figure class="fig fig--wide">
  <img src="{{ '/assets/examples/g249-11/figure1.png' | relative_url }}" alt="G 249-11 photometry folded at 5.3074 days: the same 3,000 ppm dip in sector 19 (2019), sectors 59-60 (2022-23) and the QLP full-frame light curves of sectors 73 and 86 (2023-24), each with the same transit model, and the 13 individual 2-minute transits offset vertically" loading="lazy">
  <figcaption><strong>The same transit in every epoch.</strong> Panels (a)–(c): the data folded at the fitted ephemeris, one panel per epoch, with 15-minute bins (blue) and the maximum-posterior model from the fit to the 2-minute data (orange), the same in every panel. Panel (d): the 13 individual 2-minute transits in 30-minute bins, each with the same model.</figcaption>
</figure>

| | |
|---|---|
| **Host star** | G 249-11: an M4.5 dwarf, 29.1 pc away, TESS magnitude 12.3, 0.27 R☉ |
| **Period** | 5.307419 ± 0.000010 d |
| **Mid-transit time** | BJD<sub>TDB</sub> 2459922.9291 ± 0.0012 |
| **Depth, duration** | about 3,000 ppm; 0.86 h |
| **Size, if a planet** | 1.6 (+0.4/−0.15) R⊕ |
| **Orbit** | 0.037 AU; 4.8 times Earth's insolation; equilibrium temperature about 410 K |
| **Data** | SPOC 2-minute sectors 19, 59 and 60; QLP full-frame sectors 73 and 86; 22 transits |

The evidence:

- **Detection.** A search of the three 2-minute sectors puts its highest peak at 5.30742 d,
  with S/N 11.8 and SDE 15.9 (figure below). With those transits masked, nothing else passes
  the thresholds.
- **Independent recovery.** The data outside the discovery sectors, searched alone around the
  discovery period, peak at 5.30741 d with S/N 9.8. The same search around 100 random periods
  of the same data never reached that; the highest was 9.4.
- **A steady depth.** Measured at one ephemeris: 3,210 ± 420 ppm in sector 19, 2,820 ± 350 ppm
  in sectors 59–60, 1,930 ± 670 ppm in sector 73 and 3,530 ± 700 ppm in sector 86.
- **Vetting.** Odd and even transits agree (0.0σ apart); there is no secondary eclipse; the
  transit is U-shaped; the stellar density implied by the transit agrees with the catalog
  value (0.7σ); all 13 two-minute transits are fully covered and none falls at a momentum
  dump; the star shows no rotation or short-period variation that could mimic it.
- **On the star.** The difference-image centroid is consistent with the target (offset 1.6″,
  0.1σ), and every cataloged neighbor bright enough to cause the dip is excluded at 5.1σ or
  more.

<figure class="fig fig--wide">
  <img src="{{ '/assets/examples/g249-11/figure2.png' | relative_url }}" alt="Two BLS periodograms of the 2-minute data: before masking, a peak at 5.3074 days with SDE 15.9 and its aliases; after masking, nothing passes the detection thresholds" loading="lazy">
  <figcaption><strong>One signal, and nothing else.</strong> Signal detection efficiency against trial period for sectors 19, 59 and 60. (a) The first search: the highest peak is at 5.3074 d; the other peaks above the threshold are its aliases, apart from one at 18.98 d that disappears once its transits are masked. (b) After masking the transits and detrending again: the highest peak (0.884 d) has S/N 6.2, below the threshold of 7.</figcaption>
</figure>

<div class="note note--info" markdown="1">
<span class="note__t">Not yet a planet</span>
G 249-11's signal is a candidate, not a confirmed planet, and it is not yet a TOI or a
Community TOI. TESS photometry cannot rule out an eclipsing binary bound to the star or hidden
within about 14″ of it. Settling it needs ground-based photometry of a transit,
high-resolution imaging and radial velocities (a semi-amplitude of 2.4–5.7 m/s for 2.5–6
Earth masses). The next
predicted transit times are in
[`derived_values.txt`]({{ site.github_url }}/blob/main/results/g249-11/derived_values.txt).
</div>

## Wolf 1530 (TIC 88756273): a weak lead

A 3.694-day signal at S/N 9.3 over three sectors, which would be about 1.1 Earth radii. Its
transits are short and near-grazing (0.44 h), and the one later sector agrees only at a level
that noise reaches about 3 % of the time. It is worth checking again when TESS next observes
the star.

## Every other signal

| outcome | sectors 1–26 | sectors 27–83 |
|---|---|---|
| strong candidate | – | 1 |
| weak lead | – | 1 |
| known eclipsing binary | 4 | 2 |
| light from a neighboring star | 2 | – |
| starspots, or a short-period variation | 4 | 3 |
| instrumental | 4 | 5 |
| transit far too long for the star | – | 2 |
| not confirmed by the star's other TESS years, so most likely noise | 12 | 22 |
| **signals checked** | **26** | **36** |

**Sectors 1–26 (TESS years 1 and 2).**

- **Known eclipsing binaries, 4 signals:** TIC 199574208 (CM Draconis, found at half its
  1.268-day period); TIC 22818693 (G 165-16, found at half its 5.630-day period); TIC 233211759
  (two signals; in the TESS eclipsing-binary catalog at 100.21 d).
- **Light from a neighboring star, 2:** TIC 234305872 (a 4.06-hour eclipsing binary 19.6″
  from the target); TIC 296549760 (a crowded field, where the depth doubles in a different
  aperture).
- **Starspots, or a short-period variation, 4:** TIC 420947477, 232611241 and 309617141 (the
  dip period is the star's rotation period); TIC 395586003, G 245-36 (nine cycles of a steady
  3.97-hour variation).
- **Instrumental, 4:** TIC 219389446 (events at the edges of the data); TIC 100103201
  (momentum dumps); TIC 219369255 (a 27.1-day period, the length of a sector, made of events
  at sector edges); TIC 235687447 (flux ramps where the data resume after gaps).
- **Not confirmed by the star's other TESS years, 12:** TIC 233130965, 236783276, 309550843,
  22009405, 350345319, 243335025, 255865474, 235685961, 138332040, 275463903 (two signals)
  and 238893042.

**Sectors 27–83 (TESS years 3 to 6).**

- **Strong candidate and weak lead, 2:** TIC 417732194 (G 249-11) and TIC 88756273
  (Wolf 1530), above.
- **Known eclipsing binaries, 2:** TIC 233211759 and TIC 22818693 (G 165-16).
- **Starspots or a variable star, 3:** TIC 165530589, 284192530 and 391377753.
- **Instrumental, 5:** TIC 38459063, 294927550, 38940308, 350584005 and 391922364, all dipping
  at the same moment (BTJD 2266.4, in sector 35): one spacecraft event seen in many stars.
- **Transit far too long for the star, 2:** TIC 275664367 and 118893901.
- **Not confirmed by the star's other TESS years, 22:** TIC 141185142, 141489237, 149423103,
  156463161, 167721744, 176933645, 177237464, 219865662, 230074481, 230087050, 233628527,
  238930284, 278589128, 320525039, 356735146, 381974387, 382157798, 388014766, 389501533,
  403257282, 405431193 and 99403825.

Sectors 84–96 are being searched.

## What the batches taught the pipeline

- **Check the other years.** Searching a star's other TESS years at the candidate's period
  settled most of the 62 signals and recovered G 249-11 independently. It is now
  `scripts/check_other_years.py`, and running it automatically is on the
  [roadmap](discovery.md#roadmap).
- **Know the eclipsing binaries.** Six signals came from stars already in the TESS
  eclipsing-binary catalog or in the literature as binaries; the batch's cross-match covers
  only planets and TOIs.
- **Watch for shared events.** Five stars dipped at the same moment in sector 35, which no
  planet can do.
- **Look below 0.5 days.** Two false alarms were multiples of a variation faster than the
  search's shortest period: G 245-36 and the 4.06-hour binary near TIC 234305872.
