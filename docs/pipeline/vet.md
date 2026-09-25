---
title: "Vet"
slug: vet
---

## Most dips are not planets

Of more than 8,000 TESS Objects of Interest, over 2,000 have already turned out to be false
positives ([TESS planet count](https://tess.mit.edu/tess-planet-count/)). The biggest culprit
is the **eclipsing binary** (EB): two stars orbiting each other, whose eclipses can look
exactly like a transit. Vetting looks for the fingerprints a binary leaves that a planet
cannot.

Every uncertainty in these tests is first inflated by a red-noise factor $$\beta$$: the
scatter of binned out-of-transit data divided by what white noise would give. On a star
with correlated noise, $$\beta > 1$$ makes each test harder to fail by chance.

## The seven tests

### Odd/even depths

Two similar stars eclipse each other twice per orbit, so BLS often locks on at **half** the
true period, and "odd" and "even" transits are really two different eclipses. The pipeline
fits the transit amplitude separately to odd and even epochs:

$$
\frac{\lvert\delta_{\text{odd}} - \delta_{\text{even}}\rvert}{\sqrt{\sigma_{\text{odd}}^2 + \sigma_{\text{even}}^2}} > 3 \;\Rightarrow\; \text{fail}
$$

### Secondary eclipse

A binary's second star is often luminous enough to show a dip at phase 0.5. But a hot planet
can show a small one too (its occultation), so a significant (≥ 3σ) secondary only fails if
it is deeper than **twice the largest plausible planetary occultation**, reflected light plus
thermal emission:

<div class="eq" markdown="1">

$$
\delta_{\text{occ,max}} = A_g\!\left(\frac{k}{a/R_*}\right)^{\!2} + k^2\,\frac{\int B_\lambda(T_{\text{day}})\,d\lambda}{\int B_\lambda(T_{\text{eff}})\,d\lambda}
$$

$$
T_{\text{day}} = T_{\text{eff}}\sqrt{\frac{R_*}{a}}\left(\frac23\right)^{1/4}
$$

With geometric albedo $$A_g = 1$$, a dayside with no heat redistribution, and blackbodies integrated over the 600–1000 nm TESS band. Deliberately generous, so real hot Jupiters like WASP-18 b pass.
{: .eq__note}

</div>

For eccentric orbits the secondary can fall anywhere, so a box is also scanned over all
phases. There a dip has to reach 5σ (stricter, because many phases are tried) and exceed the
same limit.

### Transit shape

A trapezoid is fitted to the folded transit. The metric is the fraction of the duration spent
in ingress and egress, $$(T_{14} - T_{23})/T_{14}$$: 0 for a box, 1 for a "V". Grazing
binaries are V-shaped, but so are grazing planets, so a value ≥ 0.8, or a posterior
probability of grazing $$P(b + k > 1) > 0.5$$, is only a **warning**.

### Stellar density

The fit measured the star's density from the transit alone. If the "planet" is really
orbiting a different, larger star (a blended background binary, or a giant), that density
won't match the catalogue. The comparison is made in log space:

$$
\frac{\lvert \ln\rho_{\text{transit}} - \ln\rho_{\text{TIC}} \rvert}{\sigma_{\ln\rho}} > 3 \;\Rightarrow\; \text{warn}, \qquad \text{and a ratio beyond } 5\times \;\Rightarrow\; \text{fail}
$$

The factor of 5 leaves room for eccentric orbits, which the circular fit can't model and
which alone bias the density by

$$
\frac{\rho_{\text{circ}}}{\rho_{\text{true}}} = \left(\frac{1 + e\sin\omega}{\sqrt{1 - e^2}}\right)^{3}.
$$

### Radius

A companion larger than 2.5 Jupiter radii is not a planet.

### Data coverage

A transit needs data inside it and on both sides. Right after a gap (the start of an orbit or
a sector) and just before one, the spacecraft's systematics are at their worst, and two
truncated dips at such edges, years apart, can pair up into a convincing long-period
"planet". A transit counts as covered if data exist for at least 75 % of its duration and for
half of a one-duration window on each side. A signal with **no** covered transit fails; one
that rests on a single covered transit gets a warning.

### Rotation period

A Lomb–Scargle periodogram of the un-detrended light curve (30-minute bins, transits masked)
finds the star's rotation period if a sinusoid explains at least 10 % of the variance. A
candidate within 5 % of half, once or twice that period gets a **warning**. Leftover spot
modulation concentrates false alarms there (see [false alarms](../validation.md#false-alarm-calibration)),
though planets can orbit there too.

## Verdicts

| outcome | verdict |
|---|---|
| any test fails | <span class="badge badge--fail">likely false positive</span> |
| warnings only | <span class="badge badge--warn">planet candidate (with caveats)</span> |
| everything passes | <span class="badge badge--pass">planet candidate (passes all tests)</span> |

## A planet and an impostor, side by side

<figure class="fig fig--wide">
  <img src="{{ '/assets/examples/SYN-3/vetting_1.png' | relative_url }}" alt="Vetting panels for SYN-3 c: odd and even depths agree, no secondary eclipse, U-shaped transit, transit-implied and catalogue densities agree; all pass" loading="lazy">
  <figcaption><strong>A planet: SYN-3 c.</strong> Odd and even transits (top left) have the same depth, there is nothing at phase 0.5 (top right), the transit is U-shaped (bottom left), and the density implied by the transit matches the catalogue (bottom right).</figcaption>
</figure>

<figure class="fig fig--wide">
  <img src="{{ '/assets/examples/SYN-5/vetting_1.png' | relative_url }}" alt="Vetting panels for eclipsing binary SYN-5: odd and even depths differ hugely (fail), no secondary, U-shaped, density far below catalogue (warn)" loading="lazy">
  <figcaption><strong>An impostor: the eclipsing binary SYN-5.</strong> The odd "transits" are twice as deep as the even ones, and the transit-implied density is a quarter of the catalogue value.</figcaption>
</figure>

| test | SYN-3 c (planet) | SYN-5 (eclipsing binary) |
|---|---|---|
| odd/even | <span class="badge badge--pass">pass</span> 3984 ± 69 vs 3860 ± 75 ppm, 1.2σ | <span class="badge badge--fail">fail</span> 17604 ± 21 vs 8891 ± 21 ppm, 297σ |
| secondary | <span class="badge badge--pass">pass</span> −87 ± 53 ppm | <span class="badge badge--pass">pass</span> 11 ± 16 ppm |
| shape | <span class="badge badge--pass">pass</span> ingress+egress 0.22 of T14 | <span class="badge badge--pass">pass</span> 0.28 of T14 |
| density | <span class="badge badge--pass">pass</span> 7.21 vs 7.11 ρ☉ (0.1σ) | <span class="badge badge--warn">warn</span> 0.28 vs 1.00 ρ☉ (11σ) |
| radius | <span class="badge badge--pass">pass</span> 0.21 R<sub>J</sub> | <span class="badge badge--pass">pass</span> 1.01 R<sub>J</sub> |
| rotation | <span class="badge badge--pass">pass</span> | <span class="badge badge--pass">pass</span> |

Values from `results/synthetic_benchmark/SYN-3/summary.md` and `SYN-5/summary.md`. The binary
passes four of six tests, which is why a pipeline needs all of them. BLS found it at half its
period, so the "transits" alternate between the two stars' eclipses, and the odd/even test
catches that at 297σ.

<div class="note note--warn" markdown="1">
<span class="note__t">What light-curve vetting cannot do</span>
None of these tests can rule out a **background binary blended into the same pixels**: its
diluted eclipses look like a planet on the target. That needs pixel-level centroid analysis
and high-resolution imaging, which are the first items on the [roadmap](../discovery.md).
"Passes all tests" means *consistent with a planet*, not *confirmed*.
</div>
