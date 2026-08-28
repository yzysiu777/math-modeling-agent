---
name: industrial-mathematical-modeling
description: Build fast, evidence-backed operations research, data analysis, hybrid models and competition papers.
metadata:
  short-description: Industrial-grade modeling and experiment race
---

# Industrial Mathematical Modeling

Use this Skill for Huawei Cup problems involving planning, networks, paths,
scheduling, allocation, multi-objective decisions, robust or stochastic models,
messy data, prediction, classification, clustering, time series or mixed
analysis-and-decision systems.

## Start with one brief

Read the root/case `AGENTS.md`, `README.md`, `case_brief.md` and the original
statement/attachments. The only required human input at startup is the case
brief. Record unknowns rather than filling them from memory. Route the case to
`optimization`, `data_analysis`, `hybrid` or `insufficient_information` and
explain the evidence.

## Core loop

1. Extract the problem contract: subproblems, inputs, outputs, objectives,
   hard constraints, fields, units, time boundaries and metrics.
2. Propose at least three methodologically different candidate routes for each
   important subproblem.
3. Build an interpretable baseline and a small hand-checkable instance.
4. Queue the cheapest experiment that can distinguish the candidates.
5. Compare candidates with the same split, instances, constraints and metrics.
6. Keep a Champion and a methodologically different Challenger until the
   strategy is clear.
7. Ask Claude for a focused C1, C2 or C3 challenge when the problem, model or
   conclusion reaches a decision point.
8. Expand only after the route survives the cheap tests; update the paper as
   experiments stabilize.

## Operations research lens

Check sets and indices, variable domains, units, objective direction, initial
and terminal conditions, conservation, capacity, timing, feasibility and the
boundary of any optimality claim. Select among exact programming, network or
dynamic programming, decomposition/relaxation, heuristics, metaheuristics,
robust/stochastic optimization and simulation optimization according to the
problem. Independently recalculate feasibility and objective values with
`scripts/model_checks.py` or a small separate checker.

## Data analysis lens

Check entity grain, keys, label construction, missingness, duplicates, outliers,
time order, train/validation/test isolation, preprocessing fit scope, leakage,
baselines, metrics, calibration, uncertainty and association-versus-causation
language. Use the data checklist and the split helper before comparing models.

## Hybrid lens

Write the upstream-to-downstream fields, types, units, time semantics, error or
scenario treatment and allowed range in the case notes. Test how upstream error,
missing predictions and extreme predictions affect downstream feasibility and
objective. Compare both a simple end-to-end baseline and separate module baselines.

## Evidence and writing

Keep source, experiment ID, code entry point, parameters, seed, result and
limitations alongside each important conclusion. A model output is not a fact
until its assumptions and checks are visible. Start the paper outline after the
first baseline, keep formulas and code aligned, and calibrate language to the
strength of the evidence.

## Project references

- `references/optimization-checklist.md`
- `references/data-analysis-checklist.md`
- `references/hybrid-checklist.md`
- `references/claims-and-evidence.md`
- `skills/model-race/SKILL.md`
- `writing/README.md`
