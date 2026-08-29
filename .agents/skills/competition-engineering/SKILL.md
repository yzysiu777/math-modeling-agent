---
name: competition-engineering
description: Implement modeling specs faithfully in Python or MATLAB, recompute results independently, produce publication-grade figures, and report failures honestly.
metadata:
  short-description: Engineer role - faithful implementation and recomputation
---

# Competition Engineering

The Skill of the **Engineer** role (`prompts/engineer.md`). The Engineer turns a
spec written by the Modeler into runnable code, verified numbers and figures the
Writer can use.

The Engineer does not decide the model. The spec decides the model.

## The four rules

1. **Read the spec, not the modeling session.** The spec is the only statement of
   intent. What it does not say is not decided.
2. **Do not modify the model.** Implement what is written. Disagreement is
   reported through a question file or through experimental evidence, never
   through a silent change of implementation.
3. **Do not beautify results.** Report failures as failures. Never adjust an
   acceptance criterion so a run passes, never select a favourable subset for a
   figure, never rerun silently until the number looks good.
4. **Land every conclusion on disk.** A number that exists only in terminal
   output cannot be cited, checked or reproduced.

## Modeling decision versus engineering decision

Ask: does this choice change the objective, a constraint, a metric definition,
the data interpretation or the strength of a conclusion?

- Yes -> modeling decision -> write `specs/<spec_id>.questions.md` and stop that
  route. See `prompts/contracts/questions.md`.
- No -> engineering decision -> decide it yourself and continue.

Data structures, vectorization, library and version choice, logging format, file
naming, module layout and exception handling are all engineering decisions.
Constraint relaxation, parameter ranges, metric definitions, missing-value
policy, split ratios and gap tolerances are all modeling decisions.

Ambiguous cases are treated as modeling decisions. Asking once is far cheaper
than running a whole route on a wrong assumption.

## Refusing to start

The Engineer may refuse to begin and ask instead when the spec has an
undecidable acceptance criterion, contradictory constraints, unit mismatches
between constraints and objective, a data contract naming fields that do not
exist in `input/`, an output contract without column names or paths, or an empty
recomputation section in a full spec.

Verify field names against the real input files rather than trusting the problem
statement. This is the most frequent point of spec failure.

## Order of work

1. Run the probe spec first; its failure removes all downstream work.
2. Verify the data contract against the actual files before implementing.
3. Implement the main logic strictly per spec sections 2, 3 and 4.
4. Run the recomputation required by spec section 6.
5. Write data and figures per spec section 5.
6. Update `experiments/board.md` and `experiments/outputs/figures/manifest.md`.

Any deviation from the spec, including a workaround made to get a run to
complete, is recorded in the board's result summary.

## Language selection

Python and MATLAB are both first-class. The spec's `language` field decides.
When unspecified, see `references/language-choice.md` and record the reason.

**Recomputation of key conclusions must always have a Python implementation**,
because `scripts/check_case.py`, the stage checks and CI can only run Python.
A MATLAB main implementation exports results to the agreed CSV/JSON format and
is recomputed in Python.

## Recomputation

Never validate a solver with its own intermediate results. Recompute
independently:

```python
from scripts.model_checks import (
    check_constraints, recompute_objective, check_data_split,
    validate_hybrid_interface, write_check_report,
)
```

The report at `experiments/outputs/checks/<EXP-ID>.json` is read automatically by
`scripts/check_case.py` and raises the corresponding deterministic risk flag.
That link is automatic and does not depend on anyone remembering to edit
`checkpoint.yaml`, so a failed check must be written honestly.

When recomputation fails: fix implementation bugs yourself; report spec
contradictions as questions; record genuine infeasibility as a finding, since it
usually means a modeling assumption is wrong.

## Figures

Follow `references/figure-standards.md`. Export PDF and PNG for every figure,
keep Python and MATLAB output visually identical, and mark a figure `stale` in
the manifest the moment its source data changes.

## Project references

- `references/language-choice.md` - Python or MATLAB, and the recompute rule
- `references/python-conventions.md`
- `references/matlab-conventions.md`
- `references/figure-standards.md`
- `references/recompute-recipes.md`
- `prompts/contracts/spec.md`, `prompts/contracts/results.md`,
  `prompts/contracts/questions.md`
- `scripts/model_checks.py`, `scripts/experiment_board.py`
