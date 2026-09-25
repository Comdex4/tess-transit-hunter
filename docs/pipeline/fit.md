---
title: "Fit"
slug: fit
---
{% assign c = site.data.benchmark | where: "planet", "SYN-3 c" | first %}

## From a box to a planet

BLS finds a box. A real transit isn't box-shaped: the planet takes time to cross the star's
edge (ingress and egress), and the star is dimmer at its limb than at its centre, which
rounds the bottom. Fitting a physical model to that shape gives the planet's size, the
geometry of its orbit and, through Kepler's laws, the density of its star.

The model is **batman** (Kreidberg 2015): the exact flux blocked by an opaque disk crossing a
limb-darkened star on a circular orbit. The star's brightness profile is quadratic in
$$\mu = \cos\theta$$, the angle between the line of sight and the surface normal:

$$
\frac{I(\mu)}{I(1)} = 1 - u_1(1-\mu) - u_2(1-\mu)^2
$$

## What the shape tells you

<figure class="fig">
  <img src="{{ '/assets/site/impact_shapes.png' | relative_url }}" alt="Four model transits for the same planet at impact parameters 0, 0.5, 0.8 and 0.95: as b increases the transit gets shorter, shallower and more V-shaped" loading="lazy">
  <figcaption><strong>The same planet crossing at different impact parameters <i>b</i></strong> (0 = through the centre, 1 = grazing the edge). Off-centre transits are shorter and shallower, because the chord is shorter and the limb is darker, and they spend more of their time in ingress and egress. Drawn with the pipeline's batman model.</figcaption>
</figure>

| parameter | what it controls | prior |
|---|---|---|
| $$T_0$$ | time of mid-transit | uniform, ±1 BLS duration |
| $$P$$ | period | uniform, ±(duration × P / time span) |
| $$k = R_p/R_*$$ | depth ≈ $$k^2$$ | uniform (10⁻⁴, 1) |
| $$\ln(a/R_*)$$ | duration, via orbital speed | uniform (ln 1.2, ln 500) |
| $$b$$ | ingress/egress length, chord | uniform (0, 1 + k) |
| $$q_1, q_2$$ | limb darkening | uniform (0, 1) |
| $$f_0$$ | out-of-transit baseline | uniform (0.9, 1.1) |
| $$\ln \sigma_{\text{jit}}$$ | extra white noise | uniform (ln 10⁻⁷, ln 0.1) |

The limb-darkening coefficients are sampled in the Kipping (2013) parameterisation,

$$
u_1 = 2\sqrt{q_1}\,q_2, \qquad u_2 = \sqrt{q_1}\,(1 - 2q_2),
$$

which maps the unit square exactly onto the physically allowed laws (brightness positive
everywhere and decreasing towards the limb), so uniform priors on $$q_1, q_2$$ are
uninformative.

## The likelihood

Only data within ±2.5 durations of each transit are fitted, with the other planets'
transits removed. Each point's error bar is inflated by a jitter term that the fit learns:

<div class="eq" markdown="1">

$$
\ln \mathcal{L} = -\frac12 \sum_i \left[ \frac{\bigl(f_i - f_0\,m_i(\theta)\bigr)^2}{s_i^2} + \ln\bigl(2\pi s_i^2\bigr) \right],
\qquad s_i^2 = \sigma_i^2 + \sigma_{\text{jit}}^2
$$

</div>

## Sampling with MCMC

The posterior is explored with **emcee** (Foreman-Mackey et al. 2013), an affine-invariant
ensemble sampler. 40 walkers start near the maximum-a-posteriori point, found by optimising
from three impact parameters (0.1, 0.5, 0.8) so as not to get stuck in a grazing or
non-grazing local optimum.

A chain is treated as converged when it is longer than **50 integrated autocorrelation
times** $$\tau$$ and the estimate of $$\tau$$ has changed by less than 1 % (checked every 500
steps, 2,000 to 20,000 steps). Burn-in is $$2\tau$$ and the chain is thinned by $$\tau/2$$.
Shallow transits often hit the step limit first, because $$b$$, $$a/R_*$$, $$k$$ and limb
darkening are strongly correlated. Every report says so when that happens.

<div class="fig-pair fig--wide">
  <figure class="fig" style="margin:0">
    <img src="{{ '/assets/examples/SYN-3/fit_1.png' | relative_url }}" alt="Folded transit with binned points, the orange best-fit model and residuals below" loading="lazy">
  </figure>
  <figure class="fig" style="margin:0">
    <img src="{{ '/assets/examples/SYN-3/corner_1.png' | relative_url }}" alt="Corner plot of posterior samples showing correlations between radius ratio, a over R star, and impact parameter" loading="lazy">
  </figure>
</div>
<p class="muted" style="font-size:.88rem;margin-top:.9rem"><strong style="color:var(--ink)">SYN-3 c, fitted.</strong> Left: the folded data, 10-minute bins and the best model, with residuals. Right: the posterior. The banana-shaped correlations between <i>b</i>, <i>a</i>/R<sub>*</sub> and <i>k</i> are why shallow transits need long chains.</p>

<div class="keynums">
  <div class="keynum"><b>{{ c.rp_rec | round: 2 }} ± {{ c.rp_rec_err | round: 2 }}</b><span>recovered radius (R⊕); injected {{ c.rp_pub }}</span></div>
  <div class="keynum"><b>{{ c.period_pct | abs | round: 4 }} %</b><span>period error</span></div>
  <div class="keynum"><b>{{ c.depth_rec_ppm | round: 0 }} ppm</b><span>depth (Rp/R*)²; injected {{ c.depth_pub_ppm | round: 0 }}</span></div>
  <div class="keynum"><b>{{ c.snr | round: 1 }}</b><span>search S/N</span></div>
</div>

## Derived properties

Everything below is computed sample by sample from the chain, so uncertainties propagate
automatically. Reported values are posterior medians with 68 % intervals.

<div class="eq" markdown="1">

$$
\rho_* = \frac{3\pi}{G P^2}\left(\frac{a}{R_*}\right)^3, \qquad
R_p = k\,R_*, \qquad
\cos i = \frac{b}{a/R_*}, \qquad
T_{\text{eq}} = T_{\text{eff}}\sqrt{\frac{R_*}{2a}}
$$

The planet radius uses the TIC stellar radius, with its catalogue uncertainty drawn into every sample. $$T_{\text{eq}}$$ assumes zero albedo and full heat redistribution.
{: .eq__note}

</div>

<div class="note note--info" markdown="1">
<span class="note__t">Why the star's density is not a prior</span>
Most transit fitters tie $$a/R_*$$ to the catalogue stellar density. This one deliberately
doesn't. The density implied by the transit shape is then an independent measurement, and
comparing it with the catalogue is one of the strongest tests for impostors
([Vet](vet.md#stellar-density)).
</div>
