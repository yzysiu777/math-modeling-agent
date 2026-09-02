"""Validate only the small, competition-critical workspace contract."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Iterable, List

import yaml

try:
    from .experiment_board import validate_experiment_board
    from .model_pool import validate_candidate_pool
    from .check_spec import validate_case_specs
except ImportError:  # pragma: no cover
    from experiment_board import validate_experiment_board
    from model_pool import validate_candidate_pool
    from check_spec import validate_case_specs


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md", "AGENTS.md", "agent.md", "REVIEWER.md", "Makefile",
    "protocol/competition-workflow.md", "templates/checkpoint.yaml",
    "templates/experiment_board.md", "templates/independent_review_packet.md",
    "templates/spec.md", "templates/现在做什么.md", "templates/批准单.md",
    "templates/审核卡索引.md", "templates/我的笔记.md", "scripts/create_case.py",
    "scripts/case_sources.py", "scripts/ingest.py", "scripts/check_case.py",
    "scripts/check_spec.py", "scripts/make_review_packet.py", "scripts/make_start_prompt.py",
    "prompts/modeler.md", "prompts/engineer.md", "prompts/writer.md",
    "prompts/startup/orchestrator.md", "prompts/startup/modeler.md",
    "prompts/startup/engineer.md", "prompts/startup/writer.md",
    "prompts/startup/reviewer.md", "prompts/reviewer/C1_problem_challenge.md",
    "prompts/reviewer/C2_model_challenge.md", "prompts/reviewer/C3_results_challenge.md",
    "paper/main.tex", "paper/official/2025/manifest.yaml", "paper/official/2026/manifest.yaml",
    # 案例论文骨架。第三次实测里案例只有空的 sections/，写作手自造了一份 ctexart，
    # 官方版式完全没被用到 —— 模板缺失必须当成契约破损，而不是等下一次实测发现。
    "templates/paper/main.tex", "templates/paper/config/paper-profile.tex",
    "templates/paper/sections/00-abstract.tex", "templates/paper/sections/02-restate.tex",
    "templates/paper/sections/03-symbols.tex", "templates/paper/sections/05-assumptions.tex",
    "templates/paper/sections/q1.tex", "templates/paper/sections/90-evaluation.tex",
    "templates/paper/appendix/99-programs.tex", "templates/待补图清单.md", "templates/文献清单.md",
)
RETIRED_PATHS = (
    "CLAUDE.md", "prompts/claude", "templates/claude_review_packet.md",
    "prompts/codex-start.md", "roles", ".agents/skills/industrial-mathematical-modeling",
    ".agents/skills/model-race",
    "templates/spec_probe.md", "templates/model_comparison.md", "templates/model_candidate.md",
    # 六份 writing/prompts 角色提示词：写于三角色合并之前，全仓库无人引用，
    # 内容要么已被 prompts/writer.md 与 prompts/reviewer/ 覆盖，要么与「一题一个
    # 持续 Writer 会话」矛盾。有用的写作约束已吸收进 prompts/writer.md。
    "writing/prompts",
)
# 指导文本里指向已废布局的引用。三个 Skill 曾在三轮重构里没人动过，仍教 Agent 去写
# `models/comparison.md` 这种早就删掉的文件 —— 检查器抓不到，因为它只看文件在不在，
# 不看有没有人还在引用它。口径分叉不会报错，只会让两个 Agent 各做各的。
RETIRED_REFERENCES = (
    "models/candidates.md", "models/comparison.md", "templates/spec_probe.md",
    "templates/model_candidate.md", "templates/model_comparison.md",
    "experiments/board.md", "experiments/outputs/", "experiments/code/",
    "reports/stage-0",
)
GUIDANCE_DIRS = (".agents", "prompts", "protocol", "writing", "docs")
GUIDANCE_ROOT_FILES = ("README.md", "AGENTS.md", "agent.md", "REVIEWER.md")

REVIEW_FILES = (
    "REVIEWER.md", "templates/independent_review_packet.md",
)
METADATA = ("reviewer_provider", "reviewer_model", "review_session", "saw_main_conversation", "critical_node")
RUNTIME_GMCMTHESIS_SHA256 = "2757ead1fd932291f705d5686bedf37d3463e030d821d8f7815ac7dcfee4c7aa"


def _missing(paths: Iterable[str]) -> List[str]:
    return [path for path in paths if not (ROOT / path).exists()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _official_profile_errors() -> List[str]:
    errors: List[str] = []
    try:
        runtime_class = ROOT / "paper/gmcmthesis.cls"
        if _sha256(runtime_class) != RUNTIME_GMCMTHESIS_SHA256:
            errors.append("runtime gmcmthesis.cls changed without updating the reviewed checksum")
        current = yaml.safe_load((ROOT / "paper/official/2025/manifest.yaml").read_text(encoding="utf-8"))
        for source in current.get("sources", []):
            reference = source.get("local_reference")
            path = ROOT / "paper/official/2025" / str(reference or "")
            if not reference or not path.is_file() or _sha256(path) != source.get("sha256"):
                errors.append(f"2025 official snapshot missing or changed: {reference}")
        pending = yaml.safe_load((ROOT / "paper/official/2026/manifest.yaml").read_text(encoding="utf-8"))
        if pending.get("active") is not False or pending.get("status") != "pending_official_paper_standard":
            errors.append("2026 official profile must remain inactive and pending")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"official profile validation failed: {exc}")
    return errors


def _guidance_files() -> List[Path]:
    found = [ROOT / name for name in GUIDANCE_ROOT_FILES]
    for directory in GUIDANCE_DIRS:
        found.extend(sorted((ROOT / directory).rglob("*.md")))
    return [path for path in found if path.is_file()]


def _retired_reference_errors() -> List[str]:
    errors: List[str] = []
    for path in _guidance_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in RETIRED_REFERENCES:
            if marker in text:
                errors.append(
                    f"guidance still points at the retired layout: "
                    f"{path.relative_to(ROOT).as_posix()} -> {marker}"
                )
    return errors


def validate_static_contract() -> List[str]:
    errors = [f"missing required file: {path}" for path in _missing(REQUIRED_FILES)]
    errors.extend(f"retired path is still active: {path}" for path in RETIRED_PATHS if (ROOT / path).exists())
    for relative in REVIEW_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in METADATA:
            if marker not in text:
                errors.append(f"review card/protocol missing diagnostic field {marker}: {relative}")
    errors.extend(_retired_reference_errors())
    workflow = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
    for marker in ("## A 定题", "## B 试跑", "## C 出结果", "## D 写本题", "## E 全案例收官", "## STAGE 对照"):
        if marker not in workflow:
            errors.append(f"competition workflow missing marker: {marker}")
    if "研究模式" in workflow and "不是另一种运行模式" not in workflow:
        errors.append("workspace must not revive a second research-mode pipeline")
    template = (ROOT / "templates/independent_review_packet.md").read_text(encoding="utf-8")
    if len(template.encode("utf-8")) > 6144:
        errors.append("review-card template exceeds 6 KiB")
    for path in sorted((ROOT / "prompts/startup").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for marker in ("当前子问题：Q<k>", "本题目录：<案例目录>/q<k>"):
            if marker not in text:
                errors.append(f"startup template missing question slot {marker}: {path.relative_to(ROOT)}")
    for route in ("optimization", "data-analysis", "hybrid"):
        board = ROOT / f"cases/examples/{route}/q1/board.md"
        candidates = ROOT / f"cases/examples/{route}/q1/brief.md"
        errors.extend(f"{board}: {error}" for error in validate_experiment_board(board))
        errors.extend(f"{candidates}: {error}" for error in validate_candidate_pool(candidates))
        errors.extend(
            f"cases/examples/{route}: {error}"
            for error in validate_case_specs(ROOT / f"cases/examples/{route}")
        )
        legacy_files = [
            ROOT / f"cases/examples/{route}/case_brief.md",
            ROOT / f"cases/examples/{route}/models",
            ROOT / f"cases/examples/{route}/experiments",
        ]
        errors.extend(
            f"retired lightweight-example file is still active: {path.relative_to(ROOT)}"
            for path in legacy_files if path.exists()
        )
    errors.extend(_official_profile_errors())
    try:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True
        ).stdout.splitlines()
        if any("agent_协作控制台" in path or path.startswith("handoffs/") for path in tracked):
            errors.append("external collaboration control-plane file is tracked")
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"unable to inspect tracked files: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="validate the competition workbench")
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
