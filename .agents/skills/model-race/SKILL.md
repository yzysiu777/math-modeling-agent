---
name: model-race
description: Generate methodologically diverse modeling routes, run cheap discriminating experiments, and choose Champion/Challenger pairs.
metadata:
  short-description: Candidate model and experiment race
---

# Model Race

This Skill turns a vague competition question into a small, evidence-producing
search. It is deliberately lightweight: a route can be tested, paused or
discarded without writing a long administrative record.

## Candidate diversity

Create at least three routes per important subproblem. Vary the modeling idea,
not only a parameter: for example exact MIP versus network dynamic programming
versus a constructive heuristic; or linear regression versus a tree model
versus a time-aware baseline. For each route state assumptions, data need,
implementation/compute cost, expected advantage, risk and the cheapest falsifier.

## Experiment selection

Rank queued experiments by information value divided by cost. Prefer hand-sized
instances, small samples, synthetic edge cases, short iterations and simple
baselines. Keep the comparison protocol fixed: same split or instance set,
same metrics, same constraint tolerance and comparable resource budget.

## Champion and Challenger

The Champion is the current route selected for depth. The Challenger must use a
different method family and remain runnable. Selection considers score, stability,
interpretability, feasibility, compute cost and paper value; a human decides
when the trade-off is strategic rather than numerical.

## Failure records

When a route fails, write the smallest reproducible reason in the experiment
board: failed metric, violated constraint, leakage, instability, cost or a
stronger alternative. Preserve reusable code and observations.

## Claude timing

- C1 challenges problem semantics before the race becomes expensive;
- C2 challenges architecture and algorithm after routes exist;
- C3 challenges results and strong paper claims before final writing.

Give Claude only the compact packet needed for that node. A useful challenge
contains a different method family, a counterexample or falsification test, and
the human choice it cannot settle.
