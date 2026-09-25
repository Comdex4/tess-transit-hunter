---
title: "Injection–recovery"
slug: inject
---
{% assign cs = site.data.stats.completeness %}

## Measuring what you miss

Finding nothing around a star doesn't mean there's nothing there. To say what the search
*could* have found, you plant fake planets in the data and see how many come back. The
fraction recovered is the pipeline's **completeness**, and every planet-occurrence rate or
"no planet larger than X" claim depends on it.

## The procedure

1. Draw a planet in a period × radius cell: period and radius log-uniform within the cell,
   impact parameter uniform in [0, 0.9], epoch uniform within the first period, circular
   orbit around the host's mass and radius.
2. **Multiply** its batman model into the light curve **before** detrending, so any damage
   the detrending does to transits counts against the pipeline.
3. Run the same detrend and iterative search (two iterations) as for a real star.
4. Count it as **recovered** if a detected signal matches in both period and time:

<div class="eq" markdown="1">

$$
\frac{\lvert P_{\text{found}} - P_{\text{inj}} \rvert}{P_{\text{inj}}} < 1\%
\quad\text{and}\quad
\lvert t_{\text{found}} - t_{\text{inj}} \rvert < \tfrac12 D_{\text{inj}} \text{ for some injected transit}
$$

Detections at 1/3, 1/2, 2 or 3 times the period that line up in time are recorded as aliases and **not** counted.
{: .eq__note}

</div>

Each cell's completeness is a binomial fraction, with uncertainty

$$
C = \frac{n_{\text{rec}}}{n_{\text{inj}}}, \qquad \sigma_C \approx \sqrt{\frac{C(1-C)}{n_{\text{inj}}}},
$$

so with 32 injections per cell a 50 % cell is known to about ±9 %.

<div class="keynums">
  <div class="keynum"><b>{{ cs.n_injections }}</b><span>injections, 32 per cell over an 8 × 8 grid</span></div>
  <div class="keynum"><b>{{ cs.overall_pct | round: 1 }} %</b><span>recovered overall (0.7–8 R⊕, 0.5–20 d)</span></div>
  <div class="keynum"><b>0</b><span>found only at an alias period</span></div>
  <div class="keynum"><b>≈ 9 s</b><span>of CPU per injection; runs in parallel and resumes</span></div>
</div>

## The completeness map

For a simulated two-sector light curve of a Sun-like star with 140 ppm of scatter per hour.
Hover over a cell for the counts.

<script type="application/json" id="completeness-data">{{ site.data.completeness | jsonify }}</script>
<div class="widget">
  <div class="widget__head">
    <h3>Fraction of injected planets recovered</h3>
    <p>{{ site.data.completeness.label }} · percentage recovered in each cell</p>
  </div>
  <div class="widget__body">
    <div class="heatmap" data-heatmap="completeness-data"></div>
    <div class="legend-ramp"><span>0 %</span><i></i><span>100 %</span></div>
  </div>
</div>

<figure class="fig">
  <img src="{{ '/assets/site/recovery_curves.png' | relative_url }}" alt="Recovery rate versus planet radius for four period ranges; curves rise from near zero at 0.8 Earth radii to 100 percent by 2 to 3 Earth radii, shorter periods rising first" loading="lazy">
  <figcaption><strong>The same data as recovery curves.</strong> Everything above about 2.4 R⊕ is found almost every time. Below that, the boundary depends on the period: short-period planets transit more often and stack more signal. Earth-sized planets are recovered about 70 % of the time on sub-day orbits and essentially never beyond 5 days with two sectors of data.</figcaption>
</figure>

## Why the boundary is where it is

The shape of the map follows from the signal-to-noise of a stacked transit. With
$$N_{\text{tr}} \approx B/P$$ transits of duration $$T_{14} \propto P^{1/3}$$:

<div class="eq" markdown="1">

$$
\mathrm{S/N} \approx \frac{(R_p/R_*)^2}{\sigma_{1\text{h}}}\sqrt{N_{\text{tr}}\,T_{14}[\text{h}]}
\;\propto\; R_p^2\,P^{-1/3}
$$

So at fixed S/N the smallest detectable planet grows only slowly with period, as $$R_p \propto P^{1/6}$$. Doubling the data lowers it by a factor $$2^{1/4} \approx 1.19$$.
{: .eq__note}

</div>

You can explore the same formula with the calculator on the [home page](../#main).

<div class="note note--warn" markdown="1">
<span class="note__t">An upper limit</span>
The simulated light curve has starspots and correlated noise but no spacecraft systematics
(momentum dumps, scattered light), so this map is an **upper limit** on real-data
completeness at the same noise level. The same script runs on real stars with their known
planets masked (`--tic <ID> --mask-known`); those maps appear on the
[completeness page](../completeness.md) once they have been run.
</div>
