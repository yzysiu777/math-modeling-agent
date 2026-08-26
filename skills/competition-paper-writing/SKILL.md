---
name: competition-paper-writing
description: Build evidence-backed Chinese mathematical-modeling competition papers with current official-template checks, problem-centered structure, calibrated claims, citation and AI-use auditing, and rendered-PDF quality gates.
metadata:
  short-description: Huawei Cup competition paper workflow
---

# Competition Paper Writing

Use this Skill after a model/experiment exists or when a modeling case needs a paper plan from the beginning. It controls content architecture, evidence-calibrated language, figures/tables/equations, citations, AI-use records, and final PDF delivery.

## Required reading

Read the case AGENTS.md first, then:

- writing/OFFICIAL_RULES.md
- writing/PAPER_STYLE_GUIDE.md
- writing/NATIONAL_AWARD_LANGUAGE.md
- writing/FIGURE_TABLE_FORMULA_RULES.md
- writing/AI_COMPLIANCE.md
- writing/QA_CHECKLIST.md

At competition time, also read the current official paper standard document and AI rules. They override this Skill.

## Workflow

1. Freeze the official template and record its URL, date, size, and hash.
2. Build a question-to-claim-to-evidence map before drafting.
3. Draft the abstract skeleton and result-table inventory before long prose.
4. Write each subproblem as analysis, assumptions, model, solution, results, and checks.
5. Calibrate wording to evidence; do not turn association into causation or heuristic output into global optimality.
6. Audit equations, units, figure/table numbering, cross-references, citations, code/source attribution, and AI records.
7. Run a blind/adversarial review with Claude or a human reviewer.
8. Export PDF, extract text, inspect metadata, render representative pages, and obtain human sign-off.
9. Compute final hashes and freeze the submitted PDF.

## Required artifacts

- draft/paper_plan.md
- draft/paper.md or the official Word/LaTeX source
- claim register and experiment cards
- reviews/paper_adversarial_review.md
- reviews/citation_review.md
- reviews/final_pdf_qa.md
- support/AI工具使用详情.pdf or the equivalent required by the current rules

## Failure conditions

Block delivery when the official template is unknown, the abstract exceeds the current limit, non-cover pages expose identity, a core claim lacks evidence, equations disagree with code, citations are unverifiable, AI use is undocumented when required, or the final PDF has visual/metadata defects.

## Available prompt roles

Use writing/prompts/paper_architect.md, mathematical_writer.md, figure_table_editor.md, citation_editor.md, paper_reviewer.md, and formatting_qa.md as role prompts. Keep author, reviewer, and final approver separate.
