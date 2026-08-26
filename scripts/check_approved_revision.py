"""Ensure a revision changes only human-approved files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def changed_files(base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        text=True, capture_output=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("approved_findings", type=Path)
    parser.add_argument("--base-ref", default="main")
    args = parser.parse_args()
    try:
        record = load_yaml(args.approved_findings)
        if record.get("record_type") != "approved_findings" or record.get("status") not in {"approved", "applied"}:
            print("FAIL approval record is not active", file=sys.stderr)
            return 1
        allowed = set(record.get("allowed_files", []))
        forbidden = set(record.get("forbidden_files", []))
        changed = changed_files(args.base_ref)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 2
    violations = []
    for path in changed:
        if path in forbidden or any(path.startswith(item.rstrip("/") + "/") for item in forbidden):
            violations.append(f"forbidden file changed: {path}")
        if allowed and path not in allowed:
            violations.append(f"file outside allowlist changed: {path}")
    if violations:
        print("FAIL approved revision boundary")
        print("\n".join(f"- {item}" for item in violations))
        return 1
    print("PASS approved revision boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
