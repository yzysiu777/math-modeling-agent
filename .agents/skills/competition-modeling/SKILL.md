---
name: competition-modeling
description: Generate a wide space of modeling routes, evaluate them on fixed dimensions, falsify them with one-minute probes, and write implementation specs an engineer can follow without guessing.
metadata:
  short-description: Modeler role - brainstorm, evaluate, probe, specify
---

# Competition Modeling

The Skill of the **Modeler** role (`prompts/modeler.md`). Use it for Huawei Cup
problems involving planning, networks, paths, scheduling, allocation,
multi-objective decisions, robust or stochastic models, messy data, prediction,
classification, clustering, time series or mixed analysis-and-decision systems.

The Modeler produces ideas, evaluations and specifications. Production code,
experiments and figures belong to the Engineer role; the paper belongs to the
Writer role.

## Start with one brief

Read the root `AGENTS.md`, the Stage 0 outputs (`input/题面全文.md`,
`input/说明文档/`, `input/数据清单.md`) and this question's `q<k>/数据范围.md`.
Everything you write goes into `q<k>/brief.md`; you touch only your own `q<k>/`. Record unknowns rather than filling them from memory. Route the case to
`optimization`, `data_analysis`, `hybrid` or `insufficient_information` from the
statement itself and explain the evidence; `scripts/router.py` is a keyword
prescreen only and cannot settle the route.

## Core loop

1. Extract the problem contract: subproblems, inputs, outputs, objectives,
   hard constraints, fields, units, time boundaries and metrics.
2. **Diverge**: list at least six ideas per important subproblem with no
   filtering, sampling deliberately across method families. See
   `references/brainstorming.md`.
3. **Converge**: keep at least three methodologically different routes in
   `q<k>/brief.md`, scored on the seven fixed dimensions in
   `references/route-evaluation.md`. Routes, comparison and the
   Champion/Challenger choice all live in that one file.
4. **Probe before full**: each surviving route gets two or three probe rows in
   `q<k>/board.md` -- assumption, numeric criterion, data range and budget
   written *before* the run, within 50 lines and one minute. Probes have no
   separate spec. A route does not get a full spec until its probe passes.
5. Write the full spec for surviving routes so an Engineer who cannot see this
   session can implement it without guessing. See `references/spec-writing.md`.
6. Keep a Champion and a methodologically different Challenger until the
   strategy is clear.
7. Request an Independent Reviewer challenge at C1 (problem) and C2
   (architecture). Use a fresh session, a compact packet and a different method
   family; record the reviewer metadata.

## Route diversity

Vary the modeling idea, not only a parameter: exact MIP versus network dynamic
programming versus a constructive heuristic; linear regression versus a tree
model versus a time-aware baseline. For each route state assumptions, data need,
implementation and compute cost, expected advantage, risk and the cheapest
falsifier.

`scripts/model_pool.py` only checks empty fields, invalid status, duplicate route
IDs and obvious normalized method-family duplicates. It cannot judge semantic
independence: MIP arc-flow, path-flow and time-indexed formulations are three
formulations of one route, and only C2 and human review can settle that.

## Operations research lens

Check sets and indices, variable domains, units, objective direction, initial
and terminal conditions, conservation, capacity, timing, feasibility and the
boundary of any optimality claim. Select among exact programming, network or
dynamic programming, decomposition/relaxation, heuristics, metaheuristics,
robust/stochastic optimization and simulation optimization according to the
problem. Feasibility and objective values must be recalculated independently by
the Engineer using `scripts/model_checks.py`; write that requirement into
section 6 of every full spec.

## Data analysis lens

Check entity grain, keys, label construction, missingness, duplicates, outliers,
time order, train/validation/test isolation, preprocessing fit scope, leakage,
baselines, metrics, calibration, uncertainty and association-versus-causation
language. Fix the split rule in the spec's data contract rather than leaving it
to the Engineer.

## Hybrid lens

Write the upstream-to-downstream fields, types, units, time semantics, error or
scenario treatment and allowed range into the spec's data contract. Require the
Engineer to test how upstream error, missing predictions and extreme predictions
affect downstream feasibility and objective, and to compare both a simple
end-to-end baseline and separate module baselines.

## Experiment selection

Rank queued experiments by information value divided by cost. Prefer hand-sized
instances, small samples, synthetic edge cases, short iterations and simple
baselines. Keep the comparison protocol fixed: same split or instance set, same
metrics, same constraint tolerance and comparable resource budget.

## Failure records

When a route fails, write the smallest reproducible reason in
`q<k>/brief.md` and `q<k>/board.md`: failed metric, violated
constraint, leakage, instability, cost or a stronger alternative. Preserve
reusable code and observations. A probe that kills a route in one minute is a
success, not a setback.

## Evidence and writing

Keep source, experiment ID, code entry point, parameters, seed, result and
limitations alongside each important conclusion. A model output is not a fact
until its assumptions and checks are visible. Calibrate language to the strength
of the evidence: feasible, current best, optimal under stated assumptions,
globally optimal; association, predictive contribution, causation.

## File identity and hashes

Ordinary data files and experiment outputs do not require a hash. Keep their
source, acquisition date, size and a useful file list; add SHA-256 only when the
team wants to freeze a particular input, an official template or a final
submission PDF. A hash is not a substitute for data quality, mathematical checks
or reproducibility evidence.

## Project references

- `references/brainstorming.md` - diverge then converge
- `references/route-evaluation.md` - the seven scoring dimensions
- `references/spec-writing.md` - writing specs a stranger can implement
- `references/optimization-checklist.md`
- `references/data-analysis-checklist.md`
- `references/hybrid-checklist.md`
- `references/optimization-method-cards.md`
- `references/data-analysis-method-cards.md`
- `references/hybrid-method-cards.md`
- `references/claims-and-evidence.md`
- `prompts/contracts/spec.md` - the handoff contract to the Engineer
- `scripts/model_pool.py`, `scripts/experiment_board.py`, `scripts/check_spec.py`
