---
name: competition-paper-writing
description: Write and QA Chinese mathematical-modeling competition papers with evidence-calibrated language and a reusable LaTeX workflow.
metadata:
  short-description: Evidence-backed Huawei Cup paper writing
---

# Competition Paper Writing

Use this Skill as soon as a baseline produces a stable observation. The paper
is a second representation of the model and experiments, not a final-day
decoration.

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

## LaTeX collaboration

Use `paper/main.tex` as an assembler. Keep sections, figures, tables, appendix,
references and style tokens separate. Contributors work on section branches;
the shared `.bib` file is the only citation source. Compile with XeLaTeX and
biber through `make paper-ci`, then run `make qa` and inspect the rendered PDF.

## Delivery limits

Do not invent data, awards, references, results or official requirements. The
current PDF is a preview until the team verifies the current official cover,
anonymous information, page limits, fonts and AI-use instructions. Human
members inspect the final PDF before submission.
