---
layout: default
title: "The pipeline"
kicker: "How it works"
lede: "One command takes a star's TIC ID through six stages. Each stage is a separate module that can be used on its own, and each has a page here with the maths, the design decisions and figures from real pipeline runs."
---

```mermaid
flowchart TB
    subgraph S1["Find"]
        direction LR
        A["MAST archive<br/>SPOC 2-min light curves"] --> B["<b>1 · Clean</b><br/>flags, outliers,<br/>normalise, cache"] --> C["<b>2 · Detrend</b><br/>robust biweight<br/>filter"] --> D["<b>3 · Search</b><br/>iterative BLS<br/>SDE + S/N"]
        D -->|"found one: mask it,<br/>re-detrend, search again"| C
    end
    subgraph S2["Characterise"]
        direction LR
        E["<b>4 · Fit</b><br/>batman + emcee"] --> F["<b>5 · Vet</b><br/>six EB tests"] --> G["report.json<br/>summary.md, figures"]
    end
    S1 --> S2
    H["<b>6 · Inject</b><br/>fake planets through<br/>detrend + search"] -.-> S1
```

<div class="steps-grid">
{% for st in site.data.steps %}
  <a class="step-card" href="{{ st.slug | append: '.html' }}">
    <span class="step-card__n">0{{ st.n }}</span>
    <h3>{{ st.title }}</h3>
    <p>{{ st.blurb }}</p>
    <span class="step-card__mod">{{ st.module }}</span>
  </a>
{% endfor %}
</div>

## What comes out

Every run writes a folder, `reports/TIC<ID>/`:

| file | contents |
|---|---|
| `report.json` | every number: target, stellar parameters, noise, all search iterations, posterior summaries, derived quantities, vetting tests, configuration, software versions, data provenance |
| `summary.md` | human-readable summary with the vetting reasoning |
| `detrending.png` | raw flux with trend, flattened flux |
| `search_summary.png`, `periodogram_<n>.png`, `fold_<n>.png` | BLS periodograms and folded light curves per iteration |
| `fit_<n>.png`, `corner_<n>.png` | best-fitting model with residuals; posterior corner plot |
| `vetting_<n>.png` | odd/even, phase 0.5, transit shape, stellar density |

A complete example, a simulated three-planet M-dwarf system, is in
[`results/synthetic_benchmark/SYN-3/`]({{ site.github_url }}/tree/main/results/synthetic_benchmark/SYN-3).
The figures on the step pages come from that folder and from the eclipsing-binary control
SYN-5.

```bash
transit-hunter run --tic 261136679 --outdir reports/          # one real star (needs MAST access)
transit-hunter demo --outdir reports/                         # offline: synthetic 3-planet system
```

The parameter-by-parameter reference, with every default and citation, is the
[methods reference](../methods.md).
