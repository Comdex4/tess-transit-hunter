---
layout: home
title: "TESS Transit Hunter"
---
{% assign s = site.data.stats %}
<div class="stats" aria-label="Headline results">
  <div class="stat">
    <div class="stat__value">{{ s.benchmark.n_recovered }}<small>/ {{ s.benchmark.n_planets }}</small></div>
    <div class="stat__label">simulated planets recovered end to end, including a compact three-planet system</div>
    <span class="stat__src">synthetic benchmark</span>
  </div>
  <div class="stat">
    <div class="stat__value">{{ s.benchmark.max_period_err_pct | round: 3 }}<small>%</small></div>
    <div class="stat__label">worst period error; radii within {{ s.benchmark.max_radius_err_pct | round: 0 }} % of the truth</div>
    <span class="stat__src">synthetic benchmark</span>
  </div>
  <div class="stat">
    <div class="stat__value">{{ s.completeness.overall_pct | round: 1 }}<small>%</small></div>
    <div class="stat__label">of {{ s.completeness.n_injections }} injected planets (0.7–8 R⊕) found by the search</div>
    <span class="stat__src">injection–recovery</span>
  </div>
  <div class="stat">
    <div class="stat__value">{{ s.calibration.single_sector_false_alarms }}<small>/ {{ s.calibration.single_sector_trials }}</small></div>
    <div class="stat__label">false alarms in single-sector light curves that contain only noise</div>
    <span class="stat__src">false-alarm calibration</span>
  </div>
</div>

<section class="section">
  <div class="section__head">
    <p class="kicker">The problem</p>
    <h2>An Earth dims the Sun by 84 parts per million</h2>
    <p>That is the signal. Starspots change a star's brightness by thousands of ppm, the spacecraft adds its own drifts, and two stars eclipsing each other make dips that look almost exactly like a planet. Finding real planets means pulling a tiny, strictly periodic dip out of that noise, then proving it isn't one of the impostors.</p>
  </div>
  <div class="split">
    <figure class="fig" style="margin:0">
      <img src="{{ '/assets/readme/depth_vs_radius.png' | relative_url }}" alt="Transit depth versus planet radius for M, K, G and F host stars; smaller stars give deeper transits" loading="lazy">
      <figcaption><strong>Small stars are the best place to look for small planets.</strong> Depth scales as (R<sub>p</sub>/R<sub>*</sub>)², so an Earth-sized planet around a red dwarf makes a dip about seven times deeper than around the Sun.</figcaption>
    </figure>
    <div class="widget" data-snr-calc style="margin:0">
      <div class="widget__head">
        <h3>Could TESS see it?</h3>
        <p>Move the sliders to estimate the signal-to-noise of a planet the pipeline would stack.</p>
      </div>
      <div class="widget__body">
        <div class="controls">
          <div class="control"><label>Planet radius <output data-out="rp"></output></label><input type="range" name="rp" min="-0.3" max="1.2" step="0.01" value="0.2"></div>
          <div class="control"><label>Star radius <output data-out="rs"></output></label><input type="range" name="rs" min="0.15" max="2" step="0.01" value="0.5"></div>
          <div class="control"><label>Orbital period <output data-out="period"></output></label><input type="range" name="period" min="-0.3" max="1.6" step="0.01" value="0.7"></div>
          <div class="control"><label>Noise per hour <output data-out="noise"></output></label><input type="range" name="noise" min="1.5" max="3.4" step="0.01" value="2.3"></div>
          <div class="control"><label>Data <output data-out="sectors"></output></label><input type="range" name="sectors" min="1" max="13" step="1" value="2"></div>
        </div>
        <div class="readout">
          <div><b data-out="depth"></b><span>transit depth</span></div>
          <div><b data-out="t14"></b><span>duration</span></div>
          <div><b data-out="ntr"></b><span>transits in data</span></div>
          <div><b data-out="snr"></b><span>S/N (need ≥ 7)</span></div>
        </div>
        <p class="verdict" data-verdict></p>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="section__head">
    <p class="kicker">How it works</p>
    <h2>Six steps from raw photons to a verdict</h2>
    <p>Each step is its own Python module and its own page here, with the maths, the design decisions and figures from real pipeline runs.</p>
  </div>
  <div class="steps-grid">
    {% for st in site.data.steps %}
    <a class="step-card" href="{{ '/pipeline/' | append: st.slug | append: '.html' | relative_url }}">
      <span class="step-card__n">0{{ st.n }}</span>
      {% case st.slug %}
        {% when "data" %}<svg viewBox="0 0 58 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 17h8l2-3 2 5 2-2h6l2 1 2-2h8l2-9 1 9h9l2 1 2-1h6"/></svg>
        {% when "detrend" %}<svg viewBox="0 0 58 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 22c8-14 14-14 20 0s12 14 20 0 10-8 14-6" opacity=".45"/><path d="M2 26h54"/></svg>
        {% when "search" %}<svg viewBox="0 0 58 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 30h4l2-6 2 4 3-5 2 4 3-3 3 5 2-24 2 22 3-4 2 3 3-5 2 5 3-2 2 4 3-3 3 5h6"/></svg>
        {% when "fit" %}<svg viewBox="0 0 58 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 8h14c3 0 4 18 13 18s10-18 13-18h14"/><circle cx="12" cy="9" r="1.2" fill="currentColor"/><circle cx="22" cy="21" r="1.2" fill="currentColor"/><circle cx="29" cy="27" r="1.2" fill="currentColor"/><circle cx="37" cy="20" r="1.2" fill="currentColor"/><circle cx="46" cy="8" r="1.2" fill="currentColor"/></svg>
        {% when "vet" %}<svg viewBox="0 0 58 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 8h8l3 12h6l3-12h10l3 20h6l3-20h8"/></svg>
        {% when "inject" %}<svg viewBox="0 0 58 34" fill="currentColor"><rect x="2" y="2" width="12" height="9" rx="2" opacity=".25"/><rect x="16" y="2" width="12" height="9" rx="2" opacity=".5"/><rect x="30" y="2" width="12" height="9" rx="2" opacity=".75"/><rect x="44" y="2" width="12" height="9" rx="2"/><rect x="2" y="13" width="12" height="9" rx="2" opacity=".1"/><rect x="16" y="13" width="12" height="9" rx="2" opacity=".3"/><rect x="30" y="13" width="12" height="9" rx="2" opacity=".55"/><rect x="44" y="13" width="12" height="9" rx="2" opacity=".85"/><rect x="2" y="24" width="12" height="9" rx="2" opacity=".05"/><rect x="16" y="24" width="12" height="9" rx="2" opacity=".1"/><rect x="30" y="24" width="12" height="9" rx="2" opacity=".3"/><rect x="44" y="24" width="12" height="9" rx="2" opacity=".6"/></svg>
      {% endcase %}
      <h3>{{ st.title }}</h3>
      <p>{{ st.blurb }}</p>
      <span class="step-card__mod">{{ st.module }}</span>
    </a>
    {% endfor %}
  </div>
</section>

For one TIC target, **`transit-hunter run --tic <ID>`** downloads every SPOC 2-minute sector,
cleans and detrends the photometry, runs an iterative Box Least Squares search, fits each
detection with a `batman` transit model sampled by `emcee`, applies seven vetting tests, and
writes a report folder of figures plus a JSON summary.

| page | contents |
|---|---|
| [Methods](methods.md) | every processing step, with the reasoning behind the defaults |
| [Validation](validation.md) | recovery of confirmed TESS planets; false-alarm calibration; end-to-end synthetic test |
| [Completeness](completeness.md) | injection–recovery tests over a period × radius grid |
| [Candidate verdicts](candidates.md) | vetting of TESS Objects of Interest that are still planet candidates |
| [Limitations](limitations.md) | what the pipeline does not do, and where its numbers should not be trusted |

## Status of the results

<!-- BEGIN: status -->

| analysis | needs | status |
|---|---|---|
| False-alarm calibration (synthetic noise) | offline (synthetic data) | done |
| End-to-end benchmark on synthetic systems | offline (synthetic data) | done |
| Injection–recovery on a synthetic light curve | offline (synthetic data) | done |
| Validation on confirmed TESS planets | MAST + Exoplanet Archive | **not yet run** (needs network access) |
| Vetting of TOI planet candidates | MAST + Exoplanet Archive | **not yet run** (needs network access) |
| Injection–recovery on a real TESS light curve | MAST + Exoplanet Archive | **not yet run** (needs network access) |

The analyses that need the TESS archives could not be run where this repository was built: that environment's network policy blocked `mast.stsci.edu` (TESS light curves, TIC) and `exoplanetarchive.ipac.caltech.edu` (reference values, TOI catalogue). Their code is complete and tested offline against synthetic data and mocked archive responses. The result tables, figures, and summary numbers on these pages are copied from `results/` by `scripts/update_docs.py`, not typed by hand.

<!-- END: status -->

  </div>
</section>

<div class="callout-dark">
  <div>
    <p class="kicker kicker--light">The road to a discovery</p>
    <h2>From a dip to a planet</h2>
    <p>TESS has flagged over eight thousand objects of interest, and most are still unresolved. This pipeline is built to become a credible independent vetter and, eventually, to submit its own Community TOIs.</p>
    <a class="btn btn--primary" href="{{ '/discovery.html' | relative_url }}">Read the roadmap</a>
  </div>
  <ol class="funnel-mini" aria-label="Discovery funnel">
    <li>Thousands of light curves</li>
    <li>BLS detections</li>
    <li>Pass light-curve vetting</li>
    <li>Pass pixel-level vetting</li>
    <li>Community TOI</li>
    <li>Confirmed planet</li>
  </ol>
</div>

<section class="section">
  <div class="section__head">
    <p class="kicker">Reproduce it</p>
    <h2>Every number on this site comes from a script</h2>
    <p>Tables and figures are copied from <code>results/</code> by <code>scripts/update_docs.py</code>, never typed by hand.</p>
  </div>
  <div class="prose" style="margin:0;max-width:none" markdown="1">

```bash
pip install -e ".[dev]"
pytest                                               # offline test suite (synthetic data)

# offline analyses (synthetic data)
python scripts/calibrate_false_alarms.py             # noise-only false-alarm calibration
python scripts/benchmark_search_scaling.py           # search cost vs amount of data
python scripts/run_synthetic_benchmark.py            # end-to-end test with known truth
python scripts/run_injection_recovery.py --synthetic --out results/injection_synthetic

# analyses of real TESS data (need MAST + NASA Exoplanet Archive access)
python scripts/validate_known_planets.py
python scripts/vet_toi_candidates.py
python scripts/run_injection_recovery.py --tic <TIC> --mask-known --out results/injection_tic<TIC>

python scripts/update_docs.py                        # copy the new numbers into these pages
python scripts/make_site_figures.py                  # redraw the explanatory figures
```

  </div>
</section>
