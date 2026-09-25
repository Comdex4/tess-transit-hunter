---
title: "Detrend"
slug: detrend
---

## Stars are noisy

Starspots rotate in and out of view, the star's surface granulates, and PDC leaves small
drifts behind. These changes are often **10–100 times deeper** than a small planet's transit,
but they are slow: hours to days, where a transit lasts one to a few hours. Detrending uses
that difference in timescale. It estimates a smooth trend $$T(t)$$ and divides it out:

$$
\tilde f(t) = \frac{f(t)}{T(t)}
$$

<figure class="fig fig--wide">
  <img src="{{ '/assets/examples/SYN-3/detrending.png' | relative_url }}" alt="Left: raw light curve varying by several parts per thousand with an orange trend line following it. Right: the flattened light curve, flat except for downward transit spikes" loading="lazy">
  <figcaption><strong>Pipeline output for the synthetic system SYN-3.</strong> Left: the simulated M dwarf varies by about ±5 ppt from starspots; the orange line is the fitted trend. Right: after dividing it out, the transits of three planets stand out as downward spikes.</figcaption>
</figure>

## The biweight filter

The trend is a **time-windowed Tukey biweight** (Hippke et al. 2019, `wotan`). For each point,
it looks at all data within half a window (0.75 days by default) and computes a robust
"typical value" $$T$$ that satisfies

<div class="eq" markdown="1">

$$
\sum_i w(u_i)\,(f_i - T) = 0, \qquad
w(u) = \begin{cases} (1-u^2)^2 & |u| < 1 \\ 0 & |u| \ge 1 \end{cases}, \qquad
u_i = \frac{f_i - T}{c \cdot \operatorname{MAD}}
$$

It is solved by iteration, with c = 5. Points far from the local level get weight zero.
{: .eq__note}

</div>

That weight function is why the biweight suits transit searches. A plain running mean treats
every point equally, so it sags into each transit and erases part of it. The biweight treats
the few in-transit points in each window as outliers and gives them little or no weight. In
the comparison by Hippke et al. (2019) of many detrending methods, the biweight was
the most reliable for transit searches.

The light curve is split wherever there is a gap longer than half a day (for example the
mid-sector data downlink), and each segment is detrended separately so that the trend never
has to bridge a jump.

## How much of the transit survives?

A windowed filter cannot tell a transit from a starspot if the transit fills a large part of
the window. For a shallow transit that is not down-weighted, the trend dips by roughly

$$
\Delta T \approx \delta \times \frac{T_{14}}{W}
$$

where $$\delta$$ is the depth, $$T_{14}$$ the duration and $$W$$ the window. The pipeline
therefore detrends twice:

1. **Without a mask**, for the first search pass, when nothing is known yet.
2. **With every detected transit masked** (a window two durations wide) for fitting and
   vetting. Masked points are left out of the window estimates, so the trend under a transit
   comes from the out-of-transit data on either side.

<figure class="fig">
  <img src="{{ '/assets/site/detrend_depth.png' | relative_url }}" alt="Line chart of transit depth kept versus window length: with masking, about 100 percent at all windows up to 1.5 days; without masking, the kept depth falls steeply for windows shorter than 0.5 days" loading="lazy">
  <figcaption><strong>Depth kept by the filter, measured with the pipeline's own <code>detrend()</code>.</strong> A 2.5 R⊕, 3.5-hour transit in a spotted Sun-like star. With the transits masked (blue), the depth is preserved to within about 1 % for windows from 0.25 to 1.5 days. Unmasked (orange), short windows eat the transit: at 0.35 days only about 70 % survives. The 0.75-day default keeps about 90 % in the first pass, and the masked re-detrend recovers the rest before fitting.</figcaption>
</figure>

<div class="note note--info" markdown="1">
<span class="note__t">Why not just use a longer window?</span>
A longer window follows fast starspot changes less closely and leaves more variability
behind, which raises the noise floor and creates false alarms at the rotation period. The
window is a trade-off, which is why it is a command-line option (`--window`).
</div>

## Masking again after every detection

Each time the search finds a planet, the **raw** light curve is detrended again with all
transits found so far masked, before the search looks for the next one. An unmasked trend dips
slightly under every transit and leaves small positive "shoulders" either side of it. Those
shoulders repeat at the planet's period, and folded at a subharmonic P/n they can stack into a
spurious signal. Re-detrending with a mask removes them.
