"""Validate the case evidence graph used by G9 and revision closure.

The graph checker only reads records and files.  It never executes a command
stored in a record.  A supported important claim must be connected to an
experiment or derivation evidence, a hashed output artifact, and a paper
locator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
GIT_REVISION_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
IMPORTANT_STATUSES = {"supported", "supported_with_limits"}
IMPORTANT_LEVELS = {"P0", "P1", "P2"}
FIGURE_TABLE_KINDS = {"figure", "table"}


def load_record(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(raw: object) -> str:
    path = PurePosixPath(str(raw).replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        raise ValueError(f"path must be relative and confined: {raw}")
    return str(path)


def _allowed_git_commit(workspace: Path, revision: str) -> bool:
    """Require a real commit reachable from the current repository HEAD."""

    object_check = subprocess.run(
        ["git", "-C", str(workspace), "cat-file", "-e", f"{revision}^{{commit}}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if object_check.returncode != 0:
        return False
    ancestry = subprocess.run(
        ["git", "-C", str(workspace), "merge-base", "--is-ancestor", revision, "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return ancestry.returncode == 0


def _records_by_id(records: Iterable[dict], record_type: str, label: str, errors: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"{label}[{index}] is not a mapping")
            continue
        if record.get("record_type") != record_type:
            errors.append(f"{label}[{index}] is not {record_type}")
        record_id = record.get({
            "artifact_record": "artifact_id",
            "claim_record": "claim_id",
            "experiment_record": "experiment_id",
        }.get(record_type, "id"))
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"{label}[{index}] has no stable ID")
            continue
        if record_id in result:
            errors.append(f"duplicate {record_type} ID: {record_id}")
        result[record_id] = record
    return result


def validate_evidence_graph(
    manifest: dict,
    artifacts: Iterable[dict],
    claims: Iterable[dict],
    experiments: Iterable[dict],
    *,
    workspace: Path | None = None,
    manifest_path: Path | None = None,
) -> tuple[list[str], dict]:
    """Return validation errors and a durable summary of verified edges."""

    errors: list[str] = []
    verified_files: list[dict] = []
    if manifest.get("record_type") != "project_manifest":
        errors.append("manifest is not project_manifest")
    case_id = manifest.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        errors.append("manifest has no case_id")

    actual_manifest_hash: str | None = None
    if manifest_path is not None:
        if not manifest_path.is_file():
            errors.append(f"manifest file does not exist: {manifest_path}")
        else:
            actual_manifest_hash = sha256_file(manifest_path)
            verified_files.append({"path": str(manifest_path), "sha256": actual_manifest_hash})
    if workspace is None:
        errors.append("workspace is required for file and hash verification")
    else:
        workspace = workspace.resolve()

    artifact_map = _records_by_id(artifacts, "artifact_record", "artifacts", errors)
    claim_map = _records_by_id(claims, "claim_record", "claims", errors)
    experiment_map = _records_by_id(experiments, "experiment_record", "experiments", errors)

    def same_case(record: dict, label: str, record_id: str) -> None:
        if record.get("case_id") != case_id:
            errors.append(f"{label} {record_id} has a different case_id")

    def list_field(record: dict, field: str, label: str, record_id: str) -> list:
        value = record.get(field, [])
        if not isinstance(value, list):
            errors.append(f"{label} {record_id}.{field} must be a list")
            return []
        return value

    def verify_file(path_value: object, expected_hash: object, owner: str) -> str | None:
        try:
            relative = _safe_relative(path_value)
        except ValueError as exc:
            errors.append(f"{owner}: {exc}")
            return None
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
            errors.append(f"{owner}: invalid SHA-256")
            return None
        if workspace is None:
            return relative
        path = (workspace / relative).resolve()
        if workspace not in path.parents and path != workspace:
            errors.append(f"{owner}: path escapes workspace: {relative}")
            return None
        if not path.is_file():
            errors.append(f"{owner}: file does not exist: {relative}")
            return None
        actual = sha256_file(path)
        verified_files.append({"path": relative, "sha256": actual})
        if actual.lower() != expected_hash.lower():
            errors.append(f"{owner}: SHA-256 mismatch for {relative}")
        return relative

    for artifact_id, artifact in artifact_map.items():
        same_case(artifact, "artifact", artifact_id)
        path_value = artifact.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"artifact {artifact_id} has no path")
        else:
            verify_file(path_value, artifact.get("sha256"), f"artifact {artifact_id}")
        for parent_id in list_field(artifact, "parents", "artifact", artifact_id):
            if parent_id not in artifact_map:
                errors.append(f"artifact {artifact_id} references missing parent {parent_id}")
        for claim_id in list_field(artifact, "claim_ids", "artifact", artifact_id):
            if claim_id not in claim_map:
                errors.append(f"artifact {artifact_id} references missing claim {claim_id}")
        for experiment_id in list_field(artifact, "experiment_ids", "artifact", artifact_id):
            if experiment_id not in experiment_map:
                errors.append(f"artifact {artifact_id} references missing experiment {experiment_id}")
        kind = artifact.get("kind")
        if kind in FIGURE_TABLE_KINDS:
            if not list_field(artifact, "claim_ids", "artifact", artifact_id):
                errors.append(f"{kind} artifact {artifact_id} has no claim_ids")
            if not list_field(artifact, "paper_locators", "artifact", artifact_id):
                errors.append(f"{kind} artifact {artifact_id} has no paper_locators")

    for experiment_id, experiment in experiment_map.items():
        same_case(experiment, "experiment", experiment_id)
        code_revision = experiment.get("code_revision")
        if not isinstance(code_revision, str) or not GIT_REVISION_RE.fullmatch(code_revision):
            errors.append(f"experiment {experiment_id} has no immutable code_revision")
        elif workspace is None:
            errors.append(f"experiment {experiment_id} requires a Git workspace to verify code_revision")
        elif not _allowed_git_commit(workspace, code_revision):
            errors.append(f"experiment {experiment_id} code_revision is not an allowed reachable Git commit")
        input_hash = experiment.get("input_manifest_hash")
        if not isinstance(input_hash, str) or not SHA256_RE.fullmatch(input_hash):
            errors.append(f"experiment {experiment_id} has invalid input_manifest_hash")
        elif actual_manifest_hash and input_hash.lower() != actual_manifest_hash.lower():
            errors.append(f"experiment {experiment_id} input_manifest_hash does not match manifest")
        outputs = list_field(experiment, "outputs", "experiment", experiment_id)
        if not outputs:
            errors.append(f"experiment {experiment_id} has no output artifact")
        for index, output in enumerate(outputs):
            if not isinstance(output, dict):
                errors.append(f"experiment {experiment_id}.outputs[{index}] must be an object")
                continue
            artifact_id = output.get("artifact_id")
            if artifact_id not in artifact_map:
                errors.append(f"experiment {experiment_id} output references missing artifact {artifact_id}")
                continue
            artifact = artifact_map[artifact_id]
            if experiment_id not in list_field(artifact, "experiment_ids", "artifact", artifact_id):
                errors.append(f"artifact {artifact_id} does not point back to experiment {experiment_id}")
            if output.get("path") != artifact.get("path"):
                errors.append(f"experiment {experiment_id} output path disagrees with artifact {artifact_id}")
            if output.get("sha256") != artifact.get("sha256"):
                errors.append(f"experiment {experiment_id} output hash disagrees with artifact {artifact_id}")

    for claim_id, claim in claim_map.items():
        same_case(claim, "claim", claim_id)
        claim_experiments = list_field(claim, "experiments", "claim", claim_id)
        claim_artifacts = list_field(claim, "artifacts", "claim", claim_id)
        paper_locators = list_field(claim, "paper_locators", "claim", claim_id)
        for experiment_id in claim_experiments:
            if experiment_id not in experiment_map:
                errors.append(f"claim {claim_id} references missing experiment {experiment_id}")
                continue
            outputs = experiment_map[experiment_id].get("outputs", [])
            if not any(claim_id in list_field(artifact_map.get(item.get("artifact_id"), {}), "claim_ids", "artifact", str(item.get("artifact_id"))) for item in outputs if isinstance(item, dict) and item.get("artifact_id") in artifact_map):
                errors.append(f"claim {claim_id} has no output artifact linked from experiment {experiment_id}")
        for artifact_id in claim_artifacts:
            if artifact_id not in artifact_map:
                errors.append(f"claim {claim_id} references missing artifact {artifact_id}")
                continue
            if claim_id not in list_field(artifact_map[artifact_id], "claim_ids", "artifact", artifact_id):
                errors.append(f"artifact {artifact_id} does not point back to claim {claim_id}")

        if claim.get("status") in IMPORTANT_STATUSES and claim.get("importance") in IMPORTANT_LEVELS:
            derivation = list_field(claim, "derivation_evidence", "claim", claim_id)
            if not claim_experiments and not derivation:
                errors.append(f"important supported claim {claim_id} lacks experiment or derivation evidence")
            if not paper_locators:
                errors.append(f"important supported claim {claim_id} lacks paper_locators")
            if not any(artifact_map.get(artifact_id, {}).get("kind") in FIGURE_TABLE_KINDS for artifact_id in claim_artifacts):
                errors.append(f"important supported claim {claim_id} lacks a figure/table artifact")

    summary = {
        "record_type": "evidence_graph_report",
        "case_id": case_id,
        "status": "failed" if errors else "passed",
        "counts": {
            "artifacts": len(artifact_map),
            "claims": len(claim_map),
            "experiments": len(experiment_map),
        },
        "verified_files": verified_files,
        "errors": sorted(set(errors)),
    }
    return sorted(set(errors)), summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--claim", action="append", default=[])
    parser.add_argument("--experiment", action="append", default=[])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        manifest = load_record(args.manifest)
        artifacts = [load_record(Path(path)) for path in args.artifact]
        claims = [load_record(Path(path)) for path in args.claim]
        experiments = [load_record(Path(path)) for path in args.experiment]
        errors, report = validate_evidence_graph(
            manifest,
            artifacts,
            claims,
            experiments,
            workspace=args.workspace,
            manifest_path=args.manifest,
        )
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL evidence graph: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("FAIL evidence graph")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS evidence graph")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
