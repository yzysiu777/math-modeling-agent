---
name: industrial-mathematical-modeling
description: Run evidence-backed, reviewer-gated mathematical modeling workflows for operations research, data analysis, hybrid decision problems, reproducible experiments, and competition papers.
metadata:
  short-description: Industrial-grade operations and data modeling workflow
---

# Industrial Mathematical Modeling

Use this Skill for competition or research-grade tasks involving messy attachments, statistical analysis, prediction, graph/network decisions, scheduling, resource allocation, multi-objective optimization, robust/stochastic decisions, or a final technical report.

## Required workspace contract

Before acting, read the applicable `AGENTS.md`, `README.md`, `case_manifest.yaml`, `protocol/workflow.md` and `protocol/gates.md`. If the manifest is missing, create a draft and report missing decisions before making strong claims.

Use canonical roles under `roles/`: `solution_lead`, `optimization_modeler`, `data_analyst`, `data_auditor`, `independent_adversary`, `reproducibility_engineer` and paper roles. Platform adapters may map Codex and Claude to these roles but cannot change their boundaries.

## Operating rules

1. Freeze raw inputs and record source, date, size and hash.
2. Translate the problem into an explicit data/mathematical contract.
3. Build a simple, interpretable, executable baseline before complex candidates.
4. Keep claims, experiments, reviews, failures and decisions as durable artifacts.
5. Treat Codex and Claude as separate roles; agreement is not truth.
6. Require deterministic evidence, independent reproduction or explicit human approval for important claims.
7. Mark uncertainty and missing provenance; never silently fill gaps.
8. Do not run unknown executables or mutate raw inputs.

## Route-specific emphasis

### Operations optimization

Check sets, indices, variables, domains, units, objectives, hard/soft constraints, feasibility, boundary states, solver status, optimality claims, complexity and multi-objective sensitivity. Use hand-checkable or enumerated micro-instances before scale.

### Data analysis

Check entity grain, keys, labels, missingness, duplicates, outliers, time order, train/validation/test isolation, preprocessing fit scope, leakage, baselines, metrics, calibration, uncertainty and association/causation limits.

### Hybrid decisions

Freeze the upstream-to-downstream interface: field names, types, units, time semantics, uncertainty, allowed range, scenario handling and validation tests. Check how upstream error changes downstream feasibility and objective.

## Modes

- **Intake:** inventory sources, fields, units, constraints, outputs and risks.
- **Baseline:** implement the smallest verifiable model and tests.
- **Candidate:** compare model/algorithm variants through experiment records.
- **Review:** run blind or non-blind adversarial review and focused gates.
- **Reproduction:** rerun from recorded commands and versions without guessing.
- **Handoff:** summarize route, Gate status, claims, evidence, unresolved issues and next actions.

## Required artifacts

`problem_contract.md`, data dictionary/contract, input hash manifest, routing record, experiment records, claim register, review records, failure log, decision log and final handoff. For papers, add claim/evidence map, citation audit, AI-use record and final PDF QA.

## Failure conditions

Block delivery when the route or objective is unclear, key input fields/constraints are unknown, baseline cannot run, a core claim lacks evidence, data leakage is present, constraints are violated, results cannot be reproduced, the official format is unknown, or P0/P1 findings remain unresolved.

## Project-local references

- `references/claims-and-evidence.md`
- `references/optimization-checklist.md`
- `references/data-analysis-checklist.md`
- `references/hybrid-checklist.md`
- `writing/README.md` for paper delivery
