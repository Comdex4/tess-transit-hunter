# G 249-11 (TIC 417732194): the analysis behind the candidate note

These are the outputs behind the research note *A candidate transiting super-Earth around the
nearby M4.5 dwarf G 249-11 (TIC 417732194)*. The scripts that made them are in
[`scripts/g249_11/`](../../scripts/g249_11) and
[`scripts/check_other_years.py`](../../scripts/check_other_years.py). All the data are public
TESS light curves from MAST, downloaded on first use and cached after that. Run every command
from the repository root.

| Output | Command | What the note takes from it |
| --- | --- | --- |
| `discovery_s59-60/` | `transit-hunter run --tic 417732194 --sectors 59 60 --outdir <dir> --plain` | The discovery: 5.30674 d, S/N 9.5, SDE 10.8, eight transits (Section 3.1) |
| `s19-59-60/` | `transit-hunter run --tic 417732194 --sectors 19 59 60 --outdir <dir> --plain` | The search of all 2-minute data (S/N 11.8, SDE 15.9), the transit fit (Table 2), the vetting tests and centroid (Table 3) |
| `other_years.txt` | `python scripts/check_other_years.py 417732194 5.306735 56-69 --depth 3042 --duration 0.700` | Independent recovery (S/N 9.8 at 5.30741 d), all five sectors together (S/N 13.0), depths by year, short-period and rotation checks (Sections 3.2 and 3.4) |
| `transit_checks.txt`, `transit_checks.png` | `python scripts/g249_11/transit_checks.py 100` | The 100 random-window calibration (median 7.7, 95th percentile 9.1, highest 9.4), per-transit depths and per-sector χ² (Section 3.2, Table 3) |
| `derived_values.txt` | `python scripts/g249_11/derived_values.py` | a, a/R*, insolation, Teq, radial-velocity amplitudes, b from the duration (Table 2, Section 5), the predicted transit times (Table 4) |
| `figure1.png` | `python scripts/g249_11/figure1.py` | Figure 1 |
| `figure2_passes.json`, `figure2.png` | `python scripts/g249_11/figure2_compute.py`, then `python scripts/g249_11/figure2_plot.py` | Figure 2: both search passes (5.30742 d at SDE 15.9 and S/N 11.8; then 0.884 d at S/N 6.2, below threshold) |

The pipeline writes each run to `<dir>/TIC417732194/`; the two run folders here hold that
folder's contents. The text outputs are the scripts' standard output (for example
`... > results/g249-11/other_years.txt`). `figure2_compute.py` also writes the periodogram
arrays, `figure2_passes.npz` (37 MB), which are not kept in git.

The catalog values in the note's Table 1 come from TIC 8 (in the reports' `stellar`
block), Gaia DR3 (parallax, proper motion, G, RUWE) and SIMBAD (spectral type, from
Hejazi, Lépine & Nordlander 2022), queried on 2026 October 5.

## Detection and vetting with published tools

ExoFOP accepts a candidate from a Research Note of the AAS only if the methods that
detected and vetted it are themselves published in a peer-reviewed journal. These scripts
repeat the detection and vetting with such tools: Transit Least Squares (Hippke & Heller
2019, A&A 623, A39), LEO-Vetter (Kunimoto et al. 2025, AJ 170, 280) and TRICERATOPS
(Giacalone et al. 2021, AJ 161, 24). They share one data loader,
[`tess_data.py`](../../scripts/g249_11/tess_data.py) (SPOC 2-minute and QLP light curves,
wotan biweight detrending), and need `pip install transitleastsquares leo-vetter
triceratops`; the outputs here were made with transitleastsquares 2.0, leo-vetter 1.2.0,
triceratops 1.1.0, wotan 1.10 and Lightkurve 2.6.0 on Python 3.11. Run them in this order:

| Output | Command | What it gives |
| --- | --- | --- |
| `tls/` | `python scripts/g249_11/tls_search.py` | TLS searches of the discovery sectors, all 2-minute data, the other years alone and all data (`tls_search.txt`, one JSON per search, `periodograms.png`) |
| `tls/tls_depths.txt` | `python scripts/g249_11/tls_depths.py` | The depth in each sector at the candidate's period and at the highest peak of the other years (9.92 d), and whether it is the same in every sector |
| `leo_vetter/` | `python scripts/g249_11/leo_vetter_run.py` | LEO-Vetter's 17 flux-level tests on the 2-minute data and on all data, each with its metrics (`leo_vetter.txt`), the metrics files and LEO-Vetter's summary plots |
| `triceratops/` | `python scripts/g249_11/triceratops_run.py 10` | TRICERATOPS false-positive (FPP) and nearby false-positive (NFPP) probabilities over 10 runs (`triceratops.txt`, `fpp_nfpp.json`), the scenario probabilities and the stars considered |
| `../../papers/rnaas_g249-11/figure1.pdf` | `python scripts/g249_11/figure_rnaas.py` | The figure of the research note |

Each text output is the script's standard output (for example
`... | tee results/g249-11/tls/tls_search.txt`).

LEO-Vetter's pixel-level test (the difference-image centroid) also needs
[`transit-diffImage`](https://github.com/stevepur/transit-diffImage), which is installed from
GitHub, and `tess-point`; it was not run here. With both installed,
`python scripts/g249_11/leo_vetter_run.py --pixel` adds it.

The draft Research Note built on these results is in
[`papers/rnaas_g249-11`](../../papers/rnaas_g249-11).
