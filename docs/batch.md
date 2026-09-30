---
layout: default
title: "Searching many stars"
kicker: "Discovery"
lede: "Run the pipeline on hundreds of stars overnight, then rank what survives, with safeguards against the false alarms that crowd the detection thresholds."
---

So far the pipeline has run on stars chosen because something was known about them:
confirmed planets, TOIs, and stars known to have neither. A search for something new has to
run on many stars, and that changes the odds. On
[100 real stars without known planets](validation.md#false-alarms-on-real-stars), 2 gave a
detection just above the thresholds and the vetting kept both. A new planet, if there is one,
is likely to sit in that same regime, because the TESS team's own pipelines have already
searched these stars and turned the strong signals into TOIs. So `scripts/batch_search.py`
does not just run the pipeline in a loop: it ranks every candidate the vetting keeps against
a set of safeguards, and only a candidate that clears all of them is a **prospect**.

## Three steps

```bash
python scripts/batch_search.py select --out runs/mdwarfs --sectors 1-13 \
    --min-sectors 2 --teff-max 3900 --tmag-max 13 --n 1000
python scripts/batch_search.py run --out runs/mdwarfs --max-hours 9
python scripts/batch_search.py summarize --out runs/mdwarfs
```

1. **`select`** lists the stars with SPOC 2-minute light curves in the chosen sectors
   (`--sectors`, at least `--min-sectors` of them) and filters them on the TESS Input Catalog:
   magnitude (`--tmag-max`), temperature (`--teff-min`, `--teff-max`) and luminosity class
   (dwarfs by default). Stars that already host a confirmed planet or a TOI of any
   disposition are left out unless `--include-known-hosts` is given; `--n` draws that many
   at random, reproducibly (`--seed`). It also downloads the three catalogues the screening
   checks against: confirmed planets and TOIs from the NASA Exoplanet Archive, and Community
   TOIs from ExoFOP. `--tic-file` takes a list of TIC IDs instead.
2. **`run`** runs the full pipeline (search, fits, vetting, centroid test) on every star not
   finished yet, one report folder per star under `stars/`. Each star's outcome is written as
   soon as it is known, so stopping the run (Ctrl+C, `--max-hours`, a crash) loses at most the
   star in progress, and the same command continues. A star that fails, for example on a
   network error, is recorded and skipped; `--retry-failed` tries it again. Stars without a
   candidate keep only their `report.json` and `summary.md`.
3. **`summarize`** screens every candidate found so far and writes the tables below. `run`
   rewrites them every 25 stars, and `summarize` can be run by hand while `run` is going.

## The safeguards

| safeguard | rule | why |
|---|---|---|
| not already known | no match among confirmed planets, TOIs (any disposition) and Community TOIs on the same star, at the same period or at 2, 3, ½ or ⅓ of it | a period multiple counts only if the transits line up: TOI-270 d's period is 0.5 % from twice TOI-270 c's, but it is a different planet |
| a margin above the thresholds | S/N ≥ 10 and SDE ≥ 9 (the detection thresholds are 7 and 7) | on 100 real stars without planets the strongest noise peaks reached S/N 8.8 and SDE 7.9, and the two false alarms had S/N 7.7 and 8.5 |
| enough transits | at least 3 | two dips can come from anything: HD 21749's spurious 145.7-day signal rests on two |
| a clean vetting | no warnings, and a companion whose size could be checked | TOI-1401.01, a false positive with a 2.05 R_J companion, got only a caveat because its star has no catalogue radius |
| the same signal in every sector | the S/N without the sector that contributes most stays at least 3, and the depths agree (chi-square p ≥ 0.001) | systematics of one sector, or a star that only one sector's aperture takes in, make dips confined to it |

The last check splits the transits into chunks: the sectors, or for a single sector its two
spacecraft orbits. It measures the depth in each chunk from the transits alone
(`vet.chunk_consistency`), with uncertainties widened by the scatter between transits in the
same chunk, as in the odd/even test. It is a ranking aid, not a vetting test, so verdicts do
not depend on it. On the 25 [resolved TOIs](validation.md#vetting-checked-against-resolved-tois)
it flags none of the 13 planets: the lowest p-value is 0.049 (TOI-824.01), and the weakest
planet, TOI-1683.01 (S/N 7.2 from its transit depths), keeps S/N 4.4 without its stronger
orbit. It flags none of the 12 false positives either, since an eclipsing binary's eclipses
are as deep in every sector; what stops the near-threshold false alarms is the margin. The margins and limits are options of `summarize` (`--min-snr`,
`--min-sde`, `--min-transits`).

Every candidate the vetting keeps lands in one of four groups, listed in this order in
`candidates.md`, each sorted by S/N:

* **prospects**: clear every safeguard;
* **for review**: kept by the vetting but miss at least one safeguard, listed with the
  reasons (a planet near the thresholds belongs here, next to the false alarms);
* **known objects found again**: a useful check that the run works;
* **rejected by the vetting**, with the tests that failed.

## What a run writes

| file | contents |
|---|---|
| `targets.csv`, `selection.json` | the stars and the selection that produced them |
| `catalogs.json` | the known planets, TOIs and CTOIs, with the date they were downloaded (downloaded again when older than a week) |
| `stars/TIC_<id>/` | each star's report folder (every figure for stars with a candidate) and `status.json` |
| `candidates.md`, `candidates.csv` | every candidate, ranked, with its tier, the reasons, the match and the depth in each chunk |
| `stars.csv`, `summary.json` | each star's outcome and strongest search peak; counts, and the spread of the strongest peaks across the batch |
| `batch.log` | one line per star |

## Before trusting a prospect

1. Open its report folder: the search summary, the folded transit, the fit, the vetting
   panels and the centroid figure. The transits should be visible, similar to each other and
   away from the edges of the data.
2. Run it alone on all its data with full settings: `transit-hunter run --tic <TIC>`.
3. Look the star up on [ExoFOP](https://exofop.ipac.caltech.edu/tess/): objects released
   after the catalogues were downloaded are not matched.
4. Estimate a false-positive probability, for example with TRICERATOPS, which weighs the
   blends the centroid test cannot resolve. The pipeline does not do this yet.

Only then is it worth preparing a [Community TOI](discovery.md).

## Running it on your own computer

A batch is long, but the work is ordinary: any recent laptop or desktop will do, the more
cores the better. Linux and macOS work directly. On Windows, use WSL2 with Ubuntu, the
system the automated tests run on; natively on Windows the MCMC fits cannot use more than
one core, and the transit-model package may need a C compiler to install.

```bash
# Windows only, once, in PowerShell as administrator; then open "Ubuntu" from the Start menu:
#   wsl --install -d Ubuntu
# Ubuntu / WSL2, once:
sudo apt update && sudo apt install -y git python3-venv python3-pip python3-dev build-essential
python3 --version                  # must be 3.11 or newer (Ubuntu 24.04 has 3.12)

cd ~                               # inside Linux: files under /mnt/c are much slower
git clone https://github.com/Comdex4/tess-transit-hunter.git
cd tess-transit-hunter
python3 -m venv .venv
source .venv/bin/activate          # again in every new terminal
pip install -e ".[dev]"
python -m pytest -q                # a few minutes; everything should pass
```

**Before the long run, a pilot of ten minutes or so.** Two stars whose TOIs the pipeline
should find again, with short fits:

```bash
printf "435336785\n68573534\n" > pilot.txt       # the hosts of TOI-4543 and TOI-4597
python scripts/batch_search.py select --out runs/pilot --tic-file pilot.txt --include-known-hosts
python scripts/batch_search.py run --out runs/pilot --quick-fits --workers 8
```

`runs/pilot/candidates.md` should list both under "Known objects found again", matched to
TOI-4543.01 and TOI-4597.01. That checks every step on your computer: downloads, search,
fits, target pixels and catalogues. Then start the real run, for example:

```bash
python scripts/batch_search.py select --out runs/mdwarfs --sectors 1-13 \
    --min-sectors 2 --teff-max 3900 --tmag-max 13 --n 1000
python scripts/batch_search.py run --out runs/mdwarfs --workers 8 --max-hours 9
```

`--workers 8` uses the physical cores. By default the run starts one process per logical
core; with hyperthreading that doubles the processes and the memory (a few hundred MB
each) for little gain, and WSL2 gets only half of Windows' memory unless `.wslconfig` says
otherwise.

What a run costs, measured on 4 cores:

* **time**: for a star without a detection, download included, 7–16 seconds with 2 or 3
  sectors and 50–95 seconds with 6 to 13; the selection above has 588 stars with 2 sectors
  and 188 with 7 to 13, in the continuous viewing zone around the south ecliptic pole.
  `select` prints a rough total (about 7 hours on 4 cores for that selection; fewer with
  more cores), and `run` prints its own estimate as it goes. Each candidate adds its MCMC
  fit, from a few minutes to an hour; `--quick-fits` uses shorter chains (re-run prospects
  with full ones), and `--max-sectors` searches only a star's latest sectors. A trial on 20
  stars of that selection took 15 minutes on 4 cores with full fits: 12 minutes for the 19
  without a detection, 5% less than the estimate, and 3 minutes, its fit included, for one
  whose dips all fell at the edges of the data and which the vetting rejected;
* **disk**: about 2.3 MB per star and sector for the light curves in the download cache
  (`~/.cache/transit_hunter`, or `--cache-dir`), about 9 GB for the selection above, plus
  100–400 MB of target-pixel files for each star with a candidate (about 50 MB per sector,
  for the centroid test); `select` prints the estimate;
* **network**: MAST for the light curves and target pixels, the NASA Exoplanet Archive and
  ExoFOP for the catalogues. If an archive stops answering, the run waits 10 minutes and
  tries the same star again, and stops after an hour of failures; run it again later with
  `--retry-failed`.

Keep the computer awake and plugged in (on Windows, WSL stops while Windows sleeps). If it
does stop, run the same command again: a star is only counted as done once its report is
complete.

To look at the results from Windows, run `cd runs/mdwarfs && explorer.exe .` in Ubuntu:
Windows Explorer opens the folder, and the figures in each star's folder open like any
other picture. `candidates.md` reads best in an editor that shows Markdown, such as VS Code.

## Limits

* Every star with 2-minute data has been searched by the TESS Science Processing Operations
  Center, and many by other teams and by citizen scientists. Few prospects, if any, should be
  expected; most of what survives will be near-threshold signals for review.
* The screening sees only the catalogues it downloaded, so anything released since is missed.
  The pipeline does not compute a false-positive probability yet.
* The chunk check needs transits in at least two chunks. A signal whose transits all fall in
  one chunk goes to review.
* The search is the same as for a single star: the [limitations](limitations.md) of the
  search, the fits and the vetting all apply.
