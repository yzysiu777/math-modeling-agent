"""Verify that implemented checks were produced by a protected fixed runner.

Revision records are data supplied by an executor.  A runner identifier,
runner self-hash, and a pair of ``passed`` log files therefore do not prove
that a check ran.  This module verifies the runner bytes from the base Git
commit and re-runs each implemented check from an extracted baseline snapshot,
then compares the deterministic result digest with the recorded result.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

try:
    from .gate_contract import CHECK_IMPLEMENTATION_STATUS
    from .git_contract import file_sha256
except ImportError:  # pragma: no cover
    from gate_contract import CHECK_IMPLEMENTATION_STATUS
    from git_contract import file_sha256


RUNNER_ID = "trusted_check_runner"
RUNNER_SCRIPT = "scripts/run_trusted_check.py"
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def result_digest(
    check_id: object,
    status: object,
    exit_code: object,
    stdout: str,
    stderr: str,
    artifact_hashes: object,
) -> str:
    """Return the stable digest of one fixed-check result.

    Dynamic paths and timestamps are intentionally excluded.  The digest
    covers the check identity, outcome, captured output, and claimed output
    artifact hashes; the caller separately verifies those hashes against the
    current workspace.
    """

    artifacts = artifact_hashes if isinstance(artifact_hashes, dict) else {}
    payload = {
        "check_id": check_id,
        "status": status,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "artifact_hashes": {str(key): artifacts[key] for key in sorted(artifacts, key=str)},
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_relative(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        return None
    return str(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def _safe_context_path(workspace: Path, raw: object, label: str, errors: list[str], *, must_exist: bool = True) -> str | None:
    relative = _safe_relative(raw)
    if relative is None:
        errors.append(f"{label} must be a safe relative path")
        return None
    path = (workspace / relative).resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError:
        errors.append(f"{label} escapes workspace")
        return None
    if must_exist and not path.is_file():
        errors.append(f"{label} does not exist: {relative}")
        return None
    return relative


def _validate_runner_context(
    validation: dict,
    workspace: Path,
    implemented_ids: list[str],
    errors: list[str],
) -> dict | None:
    context = validation.get("runner_context")
    if not isinstance(context, dict):
        errors.append("trusted runner context is required for implemented checks")
        return None
    if context.get("check_ids") != [item.get("check_id") for item in validation.get("check_results", []) if isinstance(item, dict)]:
        errors.append("runner_context.check_ids must mirror validation check_results")
    if context.get("changed_files") != validation.get("changed_files"):
        errors.append("runner_context.changed_files must mirror the validation record")
    if context.get("change_surfaces") != validation.get("change_surfaces"):
        errors.append("runner_context.change_surfaces must mirror the validation record")
    for field, required in (
        ("approval_path", False),
        ("change_record_path", "file_allowlist" in implemented_ids),
        ("review_record_path", "independent_or_human_closure" in implemented_ids),
        ("manifest_path", False),
        ("candidate_pdf_path", "pdf_hash" in implemented_ids or "pdf_static_qa" in implemented_ids),
    ):
        raw = context.get(field)
        if raw is None:
            if required:
                errors.append(f"runner_context.{field} is required for the selected checks")
            continue
        _safe_context_path(workspace, raw, f"runner_context.{field}", errors)
    for field in ("artifact_paths", "claim_paths", "experiment_paths", "output_file_paths"):
        raw_values = context.get(field)
        if not isinstance(raw_values, list):
            errors.append(f"runner_context.{field} must be a list")
            continue
        for index, raw in enumerate(raw_values):
            _safe_context_path(workspace, raw, f"runner_context.{field}[{index}]", errors)
    for field in ("check_ids", "changed_files", "change_surfaces"):
        if not isinstance(context.get(field), list) or not context.get(field):
            errors.append(f"runner_context.{field} must be a non-empty list")
    return context


def _extract_baseline_runner(workspace: Path, base_revision: str, destination: Path) -> Path:
    archive = subprocess.run(
        ["git", "-C", str(workspace), "archive", "--format=tar", f"{base_revision}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if archive.returncode:
        raise RuntimeError(archive.stderr.decode("utf-8", errors="replace").strip() or "cannot archive the base Git revision")
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as handle:
        members = handle.getmembers()
        for member in members:
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"base Git archive contains an unsafe path: {member.name}")
            if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise RuntimeError(f"base Git archive contains a non-regular entry: {member.name}")
        handle.extractall(destination)
    runner = destination / RUNNER_SCRIPT
    if not runner.is_file():
        raise RuntimeError("base Git archive does not contain the trusted runner")
    return runner


def _append_optional(args: list[str], flag: str, value: object) -> None:
    if value is not None and value != "":
        args.extend([flag, str(value)])


def _append_list(args: list[str], flag: str, values: object) -> None:
    if not isinstance(values, list):
        return
    for value in values:
        args.extend([flag, str(value)])


def _rerun_args(
    validation: dict,
    context: dict,
    check_id: str,
    workspace: Path,
    output_path: Path,
    evidence_root: Path,
) -> list[str]:
    def relative(path: Path) -> str:
        return path.relative_to(workspace).as_posix()

    args = [
        sys.executable,
        "__BASELINE_RUNNER__",
        "--workspace", str(workspace),
        "--revision-id", str(validation["revision_id"]),
        "--case-id", str(validation["case_id"]),
        "--change-level", str(validation["change_level"]),
        "--output-record", relative(output_path),
        "--evidence-root", relative(evidence_root),
        "--base-git-revision", str(validation["base_git_revision"]),
        "--new-git-revision", str(validation["new_git_revision"]),
        "--check-id", check_id,
        "--base-ref", str(validation["base_git_revision"]),
        "--head-ref", str(validation["new_git_revision"]),
    ]
    for surface in validation.get("change_surfaces") or []:
        args.extend(["--change-surface", str(surface)])
    for path in validation.get("changed_files") or []:
        args.extend(["--changed-file", str(path)])
    _append_optional(args, "--approval-id", validation.get("approval_id"))
    _append_optional(args, "--source-review-id", validation.get("source_review_id"))
    _append_list(args, "--finding-id", validation.get("finding_ids"))
    _append_list(args, "--new-experiment-id", validation.get("new_experiment_ids"))
    for finding in validation.get("unresolved_findings") or []:
        if isinstance(finding, dict):
            _append_optional(
                args,
                "--unresolved-finding",
                "|".join(str(finding.get(key, "")) for key in ("finding_id", "severity", "statement")),
            )
    _append_optional(args, "--approval", context.get("approval_path"))
    _append_optional(args, "--change-record", context.get("change_record_path"))
    _append_optional(args, "--review-record", context.get("review_record_path"))
    _append_optional(args, "--manifest", context.get("manifest_path"))
    _append_list(args, "--artifact", context.get("artifact_paths"))
    _append_list(args, "--claim", context.get("claim_paths"))
    _append_list(args, "--experiment", context.get("experiment_paths"))
    _append_optional(args, "--candidate-pdf", context.get("candidate_pdf_path"))
    _append_optional(args, "--expected-pdf-sha256", context.get("expected_pdf_sha256"))
    _append_list(args, "--output-file", context.get("output_file_paths"))
    _append_optional(args, "--closure-id", validation.get("closure_id"))
    _append_optional(args, "--executor-id", validation.get("executor_id"))
    _append_optional(args, "--modifier-id", validation.get("modifier_id"))
    return args


def _read_result_logs(workspace: Path, result: dict, errors: list[str]) -> tuple[str, str]:
    stdout_path = _safe_context_path(workspace, result.get("stdout_path"), f"{result.get('check_id')} stdout_path", errors)
    stderr_path = _safe_context_path(workspace, result.get("stderr_path"), f"{result.get('check_id')} stderr_path", errors)
    stdout = ""
    stderr = ""
    if stdout_path is not None:
        path = workspace / stdout_path
        stdout = path.read_text(encoding="utf-8", errors="replace")
        if not isinstance(result.get("stdout_sha256"), str) or _sha256_file(path).lower() != result["stdout_sha256"].lower():
            errors.append(f"{result.get('check_id')} stdout hash is not reproducible")
    if stderr_path is not None:
        path = workspace / stderr_path
        stderr = path.read_text(encoding="utf-8", errors="replace")
        if not isinstance(result.get("stderr_sha256"), str) or _sha256_file(path).lower() != result["stderr_sha256"].lower():
            errors.append(f"{result.get('check_id')} stderr hash is not reproducible")
    return stdout, stderr


def validate_trusted_execution(
    validation: dict,
    impact: dict,
    workspace: Path,
    *,
    base_revision: str | None = None,
    approval: dict | None = None,
) -> list[str]:
    """Validate implemented check provenance and independent baseline reruns."""

    errors: list[str] = []
    results = [item for item in validation.get("check_results", []) if isinstance(item, dict)]
    implemented = [
        item for item in results
        if CHECK_IMPLEMENTATION_STATUS.get(item.get("check_id")) == "implemented"
    ]
    if not implemented:
        return []
    if validation.get("runner_id") != RUNNER_ID:
        errors.append("implemented checks require trusted_check_runner")
    runner_path = validation.get("runner_script")
    if runner_path != RUNNER_SCRIPT:
        errors.append(f"trusted runner must be protected at {RUNNER_SCRIPT}")
    runner_file = workspace / RUNNER_SCRIPT
    if not runner_file.is_file():
        errors.append("protected trusted runner does not exist in the workspace")
    recorded_runner_hash = validation.get("runner_script_sha256")
    if not isinstance(recorded_runner_hash, str) or not HEX64.fullmatch(recorded_runner_hash):
        errors.append("trusted runner self-hash is invalid")
    elif runner_file.is_file() and _sha256_file(runner_file).lower() != recorded_runner_hash.lower():
        errors.append("trusted runner self-hash does not match the current file")
    base = base_revision or validation.get("base_git_revision")
    if not isinstance(base, str) or not base:
        errors.append("trusted execution requires a base Git revision")
    elif runner_file.is_file():
        baseline_hash = file_sha256(workspace, base, RUNNER_SCRIPT)
        if baseline_hash is None:
            errors.append("trusted runner is absent from the base Git revision")
        elif not isinstance(recorded_runner_hash, str) or baseline_hash.lower() != recorded_runner_hash.lower():
            errors.append("trusted runner differs from the protected base Git revision")

    implemented_ids = [str(item.get("check_id")) for item in implemented]
    context = _validate_runner_context(validation, workspace, implemented_ids, errors)
    if context is not None:
        expected_manifest = validation.get("project_manifest_path")
        if context.get("manifest_path") != expected_manifest:
            errors.append("runner_context.manifest_path must match the validation manifest binding")
        if approval is not None and context.get("approval_path") is None:
            errors.append("runner_context.approval_path is required when the closure has an approval record")
        change_record_path = context.get("change_record_path")
        if change_record_path is not None:
            relative_change = _safe_relative(change_record_path)
            try:
                if relative_change is not None and _load_yaml(workspace / relative_change) != impact:
                    errors.append("runner_context.change_record_path does not contain the active impact record")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"runner_context.change_record_path cannot be read: {exc}")
        approval_path = context.get("approval_path")
        if approval_path is not None and approval is not None:
            relative_approval = _safe_relative(approval_path)
            try:
                if relative_approval is not None and _load_yaml(workspace / relative_approval) != approval:
                    errors.append("runner_context.approval_path does not contain the active approval record")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"runner_context.approval_path cannot be read: {exc}")
    for result in implemented:
        check_id = result.get("check_id")
        stdout, stderr = _read_result_logs(workspace, result, errors)
        expected_digest = result.get("result_digest")
        try:
            actual_digest = result_digest(check_id, result.get("status"), result.get("exit_code"), stdout, stderr, result.get("artifact_hashes"))
        except (TypeError, ValueError) as exc:
            actual_digest = None
            errors.append(f"{check_id} result_digest input is not serializable: {exc}")
        if not isinstance(expected_digest, str) or not HEX64.fullmatch(expected_digest):
            errors.append(f"{check_id} result_digest is required")
        elif actual_digest is None or expected_digest.lower() != actual_digest.lower():
            errors.append(f"{check_id} result_digest does not match recorded evidence")
        if result.get("execution_kind") != "trusted_runner" or result.get("executor") != RUNNER_ID or result.get("status") != "passed" or result.get("exit_code") != 0:
            errors.append(f"{check_id} is not a passing trusted-runner result")
    if errors or context is None:
        return sorted(set(errors))

    try:
        with tempfile.TemporaryDirectory(prefix=".mmag-trusted-rerun-", dir=str(workspace)) as rerun_root_name, tempfile.TemporaryDirectory(prefix=".mmag-baseline-runner-") as snapshot_name:
            rerun_root = Path(rerun_root_name)
            snapshot_root = Path(snapshot_name)
            baseline_runner = _extract_baseline_runner(workspace, str(base), snapshot_root)
            for index, expected in enumerate(implemented, start=1):
                check_id = str(expected.get("check_id"))
                output_path = rerun_root / f"{index:02d}-{check_id}.yaml"
                evidence_root = rerun_root / f"evidence-{index:02d}-{check_id}"
                argv = _rerun_args(validation, context, check_id, workspace, output_path, evidence_root)
                argv[1] = str(baseline_runner)
                process = subprocess.run(argv, cwd=workspace, text=True, capture_output=True, check=False)
                if process.returncode != 0:
                    errors.append(f"{check_id} protected baseline rerun failed: {process.stderr.strip() or process.stdout.strip()}")
                    continue
                if not output_path.is_file():
                    errors.append(f"{check_id} protected baseline rerun did not produce a validation record")
                    continue
                try:
                    rerun_record = _load_yaml(output_path)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{check_id} protected baseline rerun record cannot be read: {exc}")
                    continue
                rerun_results = [
                    item for item in rerun_record.get("check_results", [])
                    if isinstance(item, dict) and item.get("check_id") == check_id
                ]
                if len(rerun_results) != 1:
                    errors.append(f"{check_id} protected baseline rerun did not produce exactly one result")
                    continue
                actual = rerun_results[0]
                if actual.get("status") != expected.get("status"):
                    errors.append(f"{check_id} protected baseline result status differs from the record")
                if actual.get("exit_code") != expected.get("exit_code"):
                    errors.append(f"{check_id} protected baseline exit code differs from the record")
                if actual.get("result_digest") != expected.get("result_digest"):
                    errors.append(f"{check_id} protected baseline result digest differs from the record")
                if rerun_record.get("runner_id") != RUNNER_ID or rerun_record.get("runner_script") != RUNNER_SCRIPT:
                    errors.append(f"{check_id} protected baseline did not identify the fixed runner")
                if rerun_record.get("runner_script_sha256") != _sha256_file(baseline_runner):
                    errors.append(f"{check_id} protected baseline runner hash is not derived from the base commit")
                if rerun_record.get("runner_version") != validation.get("runner_version"):
                    errors.append(f"{check_id} protected baseline runner version differs from the record")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"protected trusted-check verification failed: {exc}")
    return sorted(set(errors))
