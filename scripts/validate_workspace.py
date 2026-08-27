"""Validate canonical role files, YAML templates and JSON Schema contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    from .gate_contract import GATE_IDS, GATES, SAFE_CHECK_IDS
except ImportError:  # pragma: no cover
    from gate_contract import GATE_IDS, GATES, SAFE_CHECK_IDS


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
TEMPLATE_DIR = ROOT / "templates"

EXPECTED_ROLES = {
    "orchestrator", "task_router", "solution_lead", "optimization_modeler",
    "data_analyst", "data_auditor", "independent_adversary",
    "reproducibility_engineer", "paper_architect", "citation_editor",
    "formatting_qa", "final_gatekeeper", "human_owner",
}
FORBIDDEN_ACTIVE_TERMS = (
    "出血性脑卒中", "智能飞行器航迹", "通用神经网络处理器", "核内调度",
    "AI_CDM_for_ICH", "FightRoute", "FlashAttention", "2023 E", "2019 F", "2025 A",
    "competition_" + "fast", "checkpoint_" + "review", "release_" + "full",
)


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_templates() -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("missing jsonschema; install requirements-dev.txt") from exc

    errors: list[str] = []
    for template in sorted(TEMPLATE_DIR.glob("*.yaml")):
        try:
            document = load_yaml(template)
            record_type = document.get("record_type") if isinstance(document, dict) else None
            schema_path = SCHEMA_DIR / f"{record_type}.schema.json"
            if not record_type or not schema_path.exists():
                errors.append(f"{template}: unknown record_type {record_type!r}")
                continue
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema)
            for error in validator.iter_errors(document):
                location = ".".join(str(item) for item in error.absolute_path)
                errors.append(f"{template}:{location}: {error.message}")
            if record_type == "project_manifest":
                gates = document.get("acceptance", {}).get("required_gates", [])
                if gates != list(GATE_IDS):
                    errors.append(f"{template}: required_gates must equal {list(GATE_IDS)}")
            if record_type in {"change_impact_record", "revision_validation_record"}:
                checks = document.get("required_checks", []) or document.get("executed_checks", [])
                unsafe = set(checks).difference(SAFE_CHECK_IDS)
                if unsafe:
                    errors.append(f"{template}: unsafe check IDs {sorted(unsafe)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{template}: {exc}")
    return errors


def extract_gate_rows(text: str) -> list[tuple[str, str, str, str]]:
    rows = []
    for line in text.splitlines():
        if not re.match(r"^\|\s*G(?:[0-9]|1[0-2])\s*\|", line):
            continue
        cells = [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4:
            rows.append(tuple(cells))
    return rows


def validate_gate_mirror(text: str) -> list[str]:
    expected_rows = [(gate.gate_id, gate.name, gate.state, gate.exit_evidence) for gate in GATES]
    return [] if extract_gate_rows(text) == expected_rows else ["full Gate ID/name/state/exit-evidence table is not canonical"]


def validate_static_contract() -> list[str]:
    errors: list[str] = []
    for role in EXPECTED_ROLES:
        if not (ROOT / "roles" / f"{role}.md").exists():
            errors.append(f"missing canonical role: {role}")

    for schema in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            json.loads(schema.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON Schema {schema}: {exc}")

    expected_gates = set(GATE_IDS)
    for relative in ("protocol/workflow.md", "protocol/gates.md", "protocol/state-machine.md"):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        found = set(re.findall(r"\bG(?:[0-9]|1[0-2])\b", text))
        if found != expected_gates:
            errors.append(f"{path}: Gate IDs {sorted(found)} do not equal {list(GATE_IDS)}")
        if re.search(r"\bG(?:1[3-9]|[2-9][0-9])\b", text):
            errors.append(f"{path}: contains Gate ID outside canonical G0-G12")
        errors.extend(f"{path}: {error}" for error in validate_gate_mirror(text))
    for state in ("gate_passed", "revision_pending", "impact_classified", "targeted_validation", "validation_passed", "validation_failed", "restore_affected_gate"):
        if state not in (ROOT / "protocol/state-machine.md").read_text(encoding="utf-8"):
            errors.append(f"protocol/state-machine.md: missing revision state {state}")
    claude_prompt_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "prompts/claude").glob("*.md")
    )
    for node in ("C1", "C2", "C3"):
        if node not in claude_prompt_text:
            errors.append(f"prompts/claude: missing critical node {node}")

    if not (ROOT / "protocol/team-collaboration.md").is_file():
        errors.append("missing protocol/team-collaboration.md")
    if not (ROOT / "scripts/run_trusted_check.py").is_file():
        errors.append("missing trusted check runner")
    if not (ROOT / "scripts/check_evidence_graph.py").is_file():
        errors.append("missing evidence graph validator")

    # Official snapshots are integrity-checked; a pending future profile must
    # remain explicitly inactive and point to the official competition site.
    try:
        profile_2025 = load_yaml(ROOT / "paper/official/2025/manifest.yaml")
        for source in profile_2025.get("sources", []):
            reference = source.get("local_reference")
            if not reference:
                errors.append("2025 official profile has a source without local_reference")
                continue
            path = (ROOT / "paper/official/2025" / reference).resolve()
            if not path.is_file():
                errors.append(f"2025 official snapshot missing: {path}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != source.get("sha256"):
                errors.append(f"2025 official snapshot hash mismatch: {path}")
        profile_2026 = load_yaml(ROOT / "paper/official/2026/manifest.yaml")
        if profile_2026.get("active") is not False or profile_2026.get("status") != "pending_official_paper_standard":
            errors.append("2026 official profile must remain inactive and pending")
        urls = [source.get("url", "") for source in profile_2026.get("sources", [])]
        if not any(url.startswith("https://cpipc.acge.org.cn/") for url in urls):
            errors.append("2026 official profile must reference the official CPIPC site")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"official profile validation failed: {exc}")

    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
        control_terms = ("COLLABORATION_PROTOCOL.md", "handoffs/", "agent_协作控制台")
        if any(any(term in path for term in control_terms) for path in tracked):
            errors.append("external collaboration control-plane file is tracked in the main repository")
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"unable to verify control-plane isolation: {exc}")

    active_dirs = ["roles", "protocol", "prompts", "schemas", "templates", "skills", "writing", "paper", "scripts"]
    for dirname in active_dirs:
        base = ROOT / dirname
        for path in base.rglob("*"):
            if not path.is_file() or "official" in path.parts:
                continue
            if path.resolve() == Path(__file__).resolve():
                continue  # this checker stores forbidden sentinels by design
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for term in FORBIDDEN_ACTIVE_TERMS:
                if term in text:
                    errors.append(f"historical hardcoding in active file {path}: {term}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates-only", action="store_true")
    args = parser.parse_args()
    try:
        errors = validate_templates() if args.templates_only else validate_templates() + validate_static_contract()
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("FAIL workspace validation")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS workspace validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
