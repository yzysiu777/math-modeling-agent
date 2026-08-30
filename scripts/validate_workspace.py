"""Validate the lightweight competition workspace contract."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is installed by the workspace setup
    yaml = None

try:
    from .experiment_board import validate_experiment_board
except ImportError:  # pragma: no cover
    from experiment_board import validate_experiment_board

try:
    from .model_pool import validate_candidate_pool
except ImportError:  # pragma: no cover
    from model_pool import validate_candidate_pool


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md", "AGENTS.md", "agent.md", "REVIEWER.md",
    "protocol/competition-workflow.md", "protocol/team-collaboration.md",
    "templates/case_brief.md", "templates/checkpoint.yaml", "templates/model_candidate.md",
    "templates/model_comparison.md", "templates/experiment_board.md",
    "templates/decision_log.md", "templates/independent_review_packet.md",
    "templates/final_checklist.md", "templates/spec.md", "templates/spec_probe.md",
    "templates/spec_questions.md", "templates/figure_manifest.md", "templates/claim_map.md",
    "scripts/router.py", "scripts/create_case.py",
    "scripts/model_checks.py", "scripts/model_pool.py", "scripts/experiment_board.py",
    "scripts/check_case.py", "scripts/check_spec.py", "scripts/make_review_packet.py",
    "scripts/case_paths.py",
    "scripts/run_demos.py",
    ".agents/skills/competition-modeling/references/optimization-method-cards.md",
    ".agents/skills/competition-modeling/references/data-analysis-method-cards.md",
    ".agents/skills/competition-modeling/references/hybrid-method-cards.md",
    ".agents/skills/competition-modeling/references/brainstorming.md",
    ".agents/skills/competition-modeling/references/route-evaluation.md",
    ".agents/skills/competition-modeling/references/spec-writing.md",
    ".agents/skills/competition-engineering/references/language-choice.md",
    ".agents/skills/competition-engineering/references/python-conventions.md",
    ".agents/skills/competition-engineering/references/matlab-conventions.md",
    ".agents/skills/competition-engineering/references/figure-standards.md",
    ".agents/skills/competition-engineering/references/recompute-recipes.md",
    "paper/main.tex", "paper/official/2025/manifest.yaml", "paper/official/2026/manifest.yaml",
)
REQUIRED_SKILLS = (
    ".agents/skills/competition-modeling/SKILL.md",
    ".agents/skills/competition-engineering/SKILL.md",
    ".agents/skills/competition-paper-writing/SKILL.md",
)
REQUIRED_PROMPTS = (
    "prompts/README.md", "prompts/modeler.md", "prompts/engineer.md", "prompts/writer.md",
    "prompts/contracts/README.md", "prompts/contracts/spec.md",
    "prompts/contracts/results.md", "prompts/contracts/questions.md",
    "prompts/reviewer/C1_problem_challenge.md",
    "prompts/startup/README.md", "prompts/startup/orchestrator.md",
    "prompts/startup/modeler.md", "prompts/startup/engineer.md",
    "prompts/startup/writer.md", "prompts/startup/reviewer.md",
    "prompts/reviewer/C2_model_challenge.md", "prompts/reviewer/C3_results_challenge.md",
    "prompts/reviewer/README.md",
)
#: Paths retired by the three-role refactor.  Keeping a second live copy of the
#: rules would let an agent load two conflicting protocols; history stays in Git.
RETIRED_PATHS = (
    "prompts/codex-start.md", "roles",
    ".agents/skills/industrial-mathematical-modeling", ".agents/skills/model-race",
)
RETIRED_REVIEWER_PATHS = (
    "CLAUDE.md", "prompts/claude", "templates/claude_review_packet.md",
)
#: 审核协议文件——必须带 reviewer_provider / review_session 等元信息标记。
#: 启动模板不在此列：它只是把 agent 指向协议的一段可复制文本，元信息由协议定义。
REVIEWER_ACTIVE_FILES = (
    "REVIEWER.md", "templates/independent_review_packet.md",
    "prompts/reviewer/README.md", "prompts/reviewer/C1_problem_challenge.md",
    "prompts/reviewer/C2_model_challenge.md", "prompts/reviewer/C3_results_challenge.md",
)
REQUIRED_EXAMPLES = (
    "cases/examples/optimization/case_brief.md",
    "cases/examples/optimization/models/candidates.md",
    "cases/examples/optimization/models/comparison.md",
    "cases/examples/optimization/experiments/board.md",
    "cases/examples/optimization/experiments/code/python/run_demo.py",
    "cases/examples/data-analysis/case_brief.md",
    "cases/examples/data-analysis/models/candidates.md",
    "cases/examples/data-analysis/models/comparison.md",
    "cases/examples/data-analysis/experiments/board.md",
    "cases/examples/data-analysis/experiments/code/python/run_demo.py",
    "cases/examples/hybrid/case_brief.md",
    "cases/examples/hybrid/models/candidates.md",
    "cases/examples/hybrid/models/comparison.md",
    "cases/examples/hybrid/experiments/board.md",
    "cases/examples/hybrid/experiments/code/python/run_demo.py",
)
def _missing(paths: Iterable[str]) -> List[str]:
    return [relative for relative in paths if not (ROOT / relative).exists()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_yaml(path: Path):
    if yaml is None:
        raise RuntimeError("PyYAML is required for official paper profile validation")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_official_profiles() -> List[str]:
    errors: List[str] = []
    try:
        profile = _load_yaml(ROOT / "paper/official/2025/manifest.yaml")
        for source in profile.get("sources", []):
            reference = source.get("local_reference")
            if not reference:
                errors.append("2025 profile source has no local_reference")
                continue
            path = ROOT / "paper/official/2025" / reference
            if not path.is_file():
                errors.append(f"2025 official snapshot missing: {path}")
            elif _sha256(path) != source.get("sha256"):
                errors.append(f"2025 official snapshot hash mismatch: {path}")
        pending = _load_yaml(ROOT / "paper/official/2026/manifest.yaml")
        if pending.get("active") is not False or pending.get("status") != "pending_official_paper_standard":
            errors.append("2026 profile must remain inactive and pending")
        if not any(str(source.get("url", "")).startswith("https://cpipc.acge.org.cn/") for source in pending.get("sources", [])):
            errors.append("2026 profile must reference the official CPIPC site")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"official profile validation failed: {exc}")
    return errors


def validate_examples() -> List[str]:
    errors: List[str] = []
    for relative in REQUIRED_EXAMPLES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing demonstration artifact: {relative}")
    for route in ("optimization", "data-analysis", "hybrid"):
        errors.extend(f"cases/examples/{route}/experiments/board.md: {error}" for error in validate_experiment_board(ROOT / f"cases/examples/{route}/experiments/board.md"))
        candidates = ROOT / f"cases/examples/{route}/models/candidates.md"
        errors.extend(f"{candidates}: {error}" for error in validate_candidate_pool(candidates))
    return errors


def validate_static_contract() -> List[str]:
    errors = [f"missing required file: {path}" for path in _missing(REQUIRED_FILES + REQUIRED_SKILLS + REQUIRED_PROMPTS)]
    for relative in RETIRED_PATHS:
        if (ROOT / relative).exists():
            errors.append(f"retired path is still active: {relative}")
    for relative in RETIRED_REVIEWER_PATHS:
        if (ROOT / relative).exists():
            errors.append(f"retired reviewer path is still active: {relative}")
    for relative in REVIEWER_ACTIVE_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "Claude" in text or "CLAUDE" in text:
            errors.append(f"active reviewer file still names a retired vendor: {relative}")
        for marker in ("reviewer_provider", "reviewer_model", "review_session", "saw_main_conversation", "critical_node"):
            if marker not in text:
                errors.append(f"active reviewer file missing metadata marker {marker}: {relative}")
    errors.extend(validate_official_profiles())
    errors.extend(validate_examples())
    readme = ROOT / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        for marker in ("五分钟", "Champion", "Challenger", "C1/C2/C3", "case_brief.md"):
            if marker not in text:
                errors.append(f"README.md missing core entry marker: {marker}")
    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
        if any("agent_协作控制台" in path or path.startswith("handoffs/") for path in tracked):
            errors.append("external collaboration control-plane file is tracked in the main repository")
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"unable to inspect tracked files: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="validate the lightweight competition workspace")
    parser.parse_args()
    errors = validate_static_contract()
    if errors:
        print("FAIL workspace validation")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS workspace validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
