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

The catalogue values in the note's Table 1 come from TIC 8 (in the reports' `stellar`
block), Gaia DR3 (parallax, proper motion, G, RUWE) and SIMBAD (spectral type, from
Hejazi, Lépine & Nordlander 2022), queried on 2026 October 5.
