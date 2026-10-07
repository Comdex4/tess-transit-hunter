# Research Note of the AAS: G 249-11

A draft [Research Note of the AAS](https://journals.aas.org/research-notes/) (RNAAS) on the
candidate transiting super-Earth around G 249-11 (TIC 417732194).

| File | What it is |
| --- | --- |
| `g249-11_rnaas.tex` | The note, in AASTeX v7 |
| `references.bib` | Its references, each checked against its DOI record |
| `figure1.pdf` | Its one figure (`figure1.png` is a preview), made by `scripts/g249_11/figure_rnaas.py` |

## Why a research note, and why these methods

ExoFOP accepts a community candidate (CTOI) only once it is published in a peer-reviewed
journal, or in a Research Note if the methods used to detect and vet it have been
published in a peer-reviewed journal and are cited. The note therefore detects and vets
the signal with published tools: Transit Least Squares (Hippke & Heller 2019), LEO-Vetter
(Kunimoto et al. 2025) and TRICERATOPS (Giacalone et al. 2021). The analysis behind every
number is in [`results/g249-11`](../../results/g249-11), with the command that makes it.

## Compiling and submitting

1. On Overleaf, open the AAS template "AASTeX Template for submissions to AAS Journals
   (ApJ-AJ-ApJS-ApJL-PSJ-RNAAS)", which provides `aastex701.cls` and
   `aasjournalv7.bst`.
2. Upload `g249-11_rnaas.tex`, `references.bib` and `figure1.pdf`, and set
   `g249-11_rnaas.tex` as the main document.
3. Fill in your e-mail address (`\email[show]{...}`). An ORCID iD is optional
   (`\author[orcid=...]{Connor D. Rice}`).
4. Read the AI-use statement in the acknowledgments and change it if it does not describe
   your use exactly; the AAS requires one.
5. Optional but worthwhile: run LEO-Vetter's pixel-level test on your own computer (see
   [`results/g249-11`](../../results/g249-11/README.md)) and add its result in one sentence
   to the Vetting section.
6. Check the length: the limit is 1,500 words in all, including the title, headers, figure
   caption and references, of which 150 are for the abstract. The AAS recommends
   `texcount -v3 -merge -incbib -dir -sub=none -utf8 -sum g249-11_rnaas.tex`, and the
   editorial office's count is final.
7. Submit through the AAS journals' submission site, choosing Research Notes. There is no
   publication charge.
