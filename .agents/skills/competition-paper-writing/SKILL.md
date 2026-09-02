---
name: competition-paper-writing
description: Write and QA Chinese mathematical-modeling competition papers with traceable numbers, evidence-calibrated language and a reusable LaTeX workflow.
metadata:
  short-description: Writer role - traceable numbers and calibrated claims
---

# Competition Paper Writing

The Skill of the **Writer** role (`prompts/writer.md`). Use it as soon as a
baseline produces a stable observation. The paper is a second representation of
the model and experiments, not a final-day decoration.

## The paper is the deliverable, the claim map is the ledger

The third dry run traced every number correctly and then wrote the traceability
into the paper: 23 experiment IDs, 21 six-decimal figures and a closing paragraph
of script paths and command-line flags. No competition paper reads like that.

Trace in `paper/claim_map.md`. Keep out of the body: experiment IDs, file names,
directories, command-line flags, checker codes and workbench vocabulary
(`board`, `SPEC`, `checkpoint`). Use `\dataref{EXP-...}` when a draft needs the
link visible -- it prints nothing in the PDF. Round to **3-4 significant digits**
in prose and tables; full precision belongs in the data files. Programs appear
once, as a two-column table in the appendix: a Chinese program name and a
one-line purpose.

## Organise by question, not by activity

Front matter (background, problem restatement, symbols, problem analysis,
assumptions) is shared; each question then gets one whole chapter running data
preprocessing -> model -> solution -> evaluation metrics -> results. The
restatement and the preprocessing subsection are where judges decide whether you
actually read the problem and touched the data, so neither may be a single
paragraph.

The case paper project is seeded by `create_case` and uses the official
`gmcmthesis` class. **Never create a second main document or change the document
class.** Build with `make paper CASE=<case> Q=q<k>`.

A figure you cannot draw is not a figure you skip: hold the slot with
`\PlaceholderFigure{what it should show}` and register one line in
`队员工作区/待补图清单.md`.

## The three rules

1. **Every number is traceable.** Each number and strong claim in the abstract,
   body and conclusion must resolve through `paper/claim_map.md` to an
   experiment ID and a file under `q<k>/outputs/data/`. A number that
   cannot be traced does not enter the paper.
2. **Polishing never changes values.** Language, structure, layout and figure
   aesthetics are the Writer's to change. Numbers, units, significant digits and
   claim strength are not. A mismatch is reported through
   the Engineer via `q<k>/log.md`, never corrected in place.
3. **Claim strength matches evidence.** Feasible, current best, optimal under
   stated assumptions, globally optimal; association, predictive contribution,
   causation. These are the distinctions judges read most closely.

## Sourcing

A paper states both what the model is and what the results are, so material
comes from three read-only classes:

- **Model truth** - the accepted Champion full spec (`q<k>/specs/SPEC-*.md` with
  `status: full`), `q<k>/brief.md` and `decisions.md`. Source for
  assumptions, symbols, formulas, constraints, algorithm structure and the
  reasoning behind route selection.
- **Result truth** - `q<k>/board.md`, `q<k>/outputs/data/`,
  `q<k>/outputs/figures/manifest.md` and `q<k>/outputs/checks/`.
- **Writing standards** - the `writing/` guides and the current official rules.

All three are read-only for the Writer. Do not reconstruct a model definition
from the code: an implementation detail is not a model definition, and a
mismatch between spec and code is something to ask about, not something for the
Writer to reconcile. Do not copy numbers out of a chat transcript.

Refuse to write a result and ask instead when a number has no file, a figure's
source experiment is absent from the board, a figure is marked `stale`, a
recomputation report contains `passed: false` that the board does not mention,
or the same quantity differs between two files.

## Required reading

Read the case brief and:

- `writing/OFFICIAL_RULES.md`
- `writing/PAPER_STYLE_GUIDE.md`
- `writing/NATIONAL_AWARD_LANGUAGE.md`
- `writing/FIGURE_TABLE_FORMULA_RULES.md`
- `writing/AI_COMPLIANCE.md`
- `writing/QA_CHECKLIST.md`

At competition time, the current official paper standard, template and AI rules
override every historical snapshot in the repository.

## Writing loop

1. Build a problem–model–experiment–figure–claim–citation map.
2. Draft the abstract skeleton and result-table inventory early.
3. For each subproblem write problem interpretation, assumptions, model,
   solution, results and checks as one coherent chain.
4. Keep the formula, implementation, experiment and prose synchronized.
5. State whether a result is feasible, a current best heuristic, optimal under
   stated assumptions or globally optimal; never blur these categories.
6. Distinguish association, prediction importance and causation.
7. Put every important number beside its experiment ID or reproducible source.
8. Run C3 on the strongest results and wording; use deterministic checks for
   citations, cross-references and PDF structure.

## What polishing may and may not do

May: rebuild raw tables into publication-grade booktabs form; unify colours,
font sizes, line widths and legend placement across all figures; add axis
labels, units, captions and annotations; rewrite log-style descriptions into
academic prose; reorder paragraphs and unify terminology.

May not: change any value or significant digit, including rounding "to look
better"; change units or conversions; raise claim strength; replot a favourable
subset; add a comparison the experiments never ran.

A figure that needs redrawing is redrawn by the Engineer rerunning its script.
Never edit a figure by hand: hand-edited figures cannot be reproduced, do not
follow data updates, and are exactly what a C3 review looks for.

## LaTeX collaboration

The document class is the community `gmcmthesis` template (2025 edition), which
owns the pledge page, title-and-abstract page, page-numbering origin, absence of
running heads and body anonymity. Do not reimplement any of that: those are the
official format, and a hand-rolled copy only drifts from it.

Use `paper/main.tex` as an assembler. Keep sections, figures, tables, appendix,
references and style tokens separate; contributors work on section branches so a
single `.tex` never has two writers at once. The shared `.bib` is the only
citation source, and it is **classic BibTeX with `gmcm.bst`** -- biblatex-only
fields such as `urldate` are silently ignored.

Do not look up LaTeX syntax under time pressure: `writing/LATEX_SNIPPETS.md` holds
copy-ready blocks for booktabs tables, spanning cells, long tables, pseudocode,
subfigures, equation systems, code appendices and citations, and
`make snippet-check` compiles every one of them against this repository's own
class -- a snippet library nobody verifies is worse than none. `make paper-example`
builds the upstream template demo when you want to see an element rendered.

Compile with `make paper-ci`, then `make qa`, then open the PDF. On Linux and in
CI add `PAPER_FONTSET=fandol`; the resulting spacing differs slightly from the
submission machine, so the final PDF must be rebuilt where it will be submitted.

## Delivery limits

Do not invent data, awards, references, results or official requirements. The
current PDF is a preview until the team verifies the current official cover,
anonymous information, page limits, fonts and AI-use instructions. Human
members inspect the final PDF before submission.
