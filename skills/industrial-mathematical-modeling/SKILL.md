---
name: industrial-mathematical-modeling
description: Run evidence-backed, reviewer-gated mathematical modeling workflows for competition problems, combining reproducible data checks, baseline-first modeling, adversarial review, and final report controls.
metadata:
  short-description: Industrial-grade math modeling workflow
---

# Industrial Mathematical Modeling

Use this Skill for research-grade or competition-grade mathematical modeling tasks involving messy attachments, statistical learning, graph/path planning, scheduling, optimization, paper comparison, reproducible experiments, or a final technical report.

## Required workspace contract

Before acting, locate and read the applicable `AGENTS.md`, `case_manifest.yaml`, `protocol/workflow.md`, and `protocol/gates.md`. If the case manifest is missing, create a draft and report the missing decisions before making strong claims.

Use the canonical role prompts under `roles/`:

- `codex_lead.md` for the main coordinator;
- `claude_adversary.md` for an independent read-only reviewer;
- `data_auditor.md`, `model_reviewer.md`, and `reproducibility_reviewer.md` for focused gates;
- `final_gatekeeper.md` for final acceptance.

## Operating rules

1. Freeze raw inputs and record source, version, size, and hash.
2. Translate the problem into an explicit data and mathematical contract before tuning models.
3. Build a simple, interpretable, executable baseline before complex candidates.
4. Keep claims, experiments, reviews, failures, and decisions as durable artifacts.
5. Treat Codex and Claude as separate roles; do not use agreement as truth.
6. Require deterministic evidence, independent reproduction, or explicit human approval for important claims.
7. Mark uncertainty and missing provenance; never silently fill gaps.
8. Do not run unknown executables or mutate raw inputs.

## Modes

- **Intake:** inventory sources, fields, units, constraints, outputs, and risks.
- **Baseline:** implement the smallest verifiable model and tests.
- **Candidate:** compare model/algorithm variants through experiment cards.
- **Review:** run blind or non-blind adversarial review and focused gates.
- **Reproduction:** rerun from recorded commands and versions without guessing.
- **Handoff:** summarize Gate status, claims, evidence, unresolved issues, and next actions.

## Domain routing

- Clinical/tabular tasks: prioritize patient-level splitting, time leakage, label construction, calibration, and association-versus-causation limits.
- Graph/trajectory tasks: prioritize graph state, edge feasibility, geometry, path constraints, probability semantics, and small-instance optimal checks.
- DAG/scheduling tasks: prioritize acyclicity, topological feasibility, resources, buffer lifetimes, capacity, SPILL closure, simulator consistency, and scale tests.

## References

- Read [claims-and-evidence.md](references/claims-and-evidence.md) when registering or reviewing claims.
- Read [task-checklists.md](references/task-checklists.md) when the case is 2023 E, 2019 F, or 2025 A.
- For paper delivery, prioritize official template/version, anonymous pages, abstract limits, numeric citations, figure/table/equation cross-references, AI disclosure, and rendered-PDF QA.
- Use writing/README.md as the entry point for paper structure, official-format versioning, language control, citation auditing, AI-use records, and final-PDF QA.
- Use root templates under `templates/` for case manifests, experiment cards, reviews, and final handoff.
