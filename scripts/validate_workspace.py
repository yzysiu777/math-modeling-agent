"""Validate canonical role files, YAML templates and JSON Schema contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{template}: {exc}")
    return errors


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

    active_dirs = ["roles", "protocol", "prompts", "schemas", "templates", "skills", "writing", "paper"]
    for dirname in active_dirs:
        base = ROOT / dirname
        for path in base.rglob("*"):
            if not path.is_file() or "official" in path.parts:
                continue
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
