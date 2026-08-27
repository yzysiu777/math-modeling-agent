"""Run the fixed, model-neutral revision checks.

Only check identifiers from :mod:`gate_contract` are accepted.  The runner
contains the command mapping in code; it never reads a shell command from a
YAML/JSON record.  Every result is accompanied by timestamped stdout/stderr
files and SHA-256 hashes so the closure checker can verify what actually ran.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable

try:
    from .check_approved_revision import validate_revision_boundary
    from .check_evidence_graph import load_record, validate_evidence_graph
    from .check_review_independence import load_record as load_review_yaml, validate_review_record
    from .gate_contract import (
        CHANGE_LEVELS,
        CHANGE_SURFACES,
        CHECK_IMPLEMENTATION_STATUS,
        SAFE_CHECK_IDS,
        required_checks_for,
    )
except ImportError:  # pragma: no cover
    from check_approved_revision import validate_revision_boundary
    from check_evidence_graph import load_record, validate_evidence_graph
    from check_review_independence import load_record as load_review_yaml, validate_review_record
    from gate_contract import CHANGE_LEVELS, CHANGE_SURFACES, CHECK_IMPLEMENTATION_STATUS, SAFE_CHECK_IDS, required_checks_for


RUNNER_ID = "trusted_check_runner"
RUNNER_VERSION = "1.0.0"
SCRIPT_RELATIVE = "scripts/run_trusted_check.py"
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative_path(raw: str) -> str:
    value = str(raw).replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        raise ValueError(f"path must be relative and confined to workspace: {raw}")
    return str(path)


def _write_log(workspace: Path, evidence_root: Path, name: str, content: str) -> tuple[str, str]:
    evidence_root.mkdir(parents=True, exist_ok=True)
    path = evidence_root / name
    path.write_text(content, encoding="utf-8")
    return str(path.relative_to(workspace).as_posix()), sha256_file(path)


def _run_fixed_command(workspace: Path, argv: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(argv, cwd=workspace, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def _git_revision(workspace: Path, ref: str) -> str | None:
    if not (workspace / ".git").exists():
        return None
    code, stdout, _ = _run_fixed_command(workspace, ["git", "rev-parse", ref])
    return stdout.strip() if code == 0 else None


def _balanced_tex(text: str) -> bool:
    braces = 0
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            braces += 1
        elif char == "}":
            braces -= 1
            if braces < 0:
                return False
    return braces == 0


def _internal_basic_syntax(workspace: Path, changed_files: list[str]) -> tuple[int, str, str]:
    argv = ["git", "diff", "--check"]
    code, stdout, stderr = _run_fixed_command(workspace, argv)
    if code:
        return code, stdout, stderr
    problems: list[str] = []
    for raw in changed_files:
        path = workspace / relative_path(raw)
        if not path.is_file() or path.suffix.lower() not in {".tex", ".sty", ".cls", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() in {".tex", ".sty", ".cls"} and not _balanced_tex(text):
            problems.append(f"unbalanced TeX braces: {raw}")
    return (1, "\n".join(problems), "") if problems else (0, "git diff --check passed; source delimiter check passed\n", "")


def _internal_file_allowlist(args: argparse.Namespace, workspace: Path) -> tuple[int, str, str]:
    if not args.approval or not args.change_record:
        return 2, "", "file_allowlist requires --approval and --change-record\n"
    approval = load_record(workspace / relative_path(args.approval))
    impact = load_record(workspace / relative_path(args.change_record))
    errors = validate_revision_boundary(
        approval,
        impact,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        workspace=workspace,
    )
    return (1, "\n".join(errors) + "\n", "") if errors else (0, "modification boundary passed\n", "")


def _internal_evidence_graph(args: argparse.Namespace, workspace: Path) -> tuple[int, str, str]:
    paths = [args.manifest, *args.artifact, *args.claim, *args.experiment]
    if not args.manifest or not args.artifact or not args.claim or not args.experiment:
        return 2, "", "claim_experiment_binding requires manifest, artifact, claim and experiment records\n"
    manifest = load_record(workspace / relative_path(args.manifest))
    artifacts = [load_record(workspace / relative_path(path)) for path in args.artifact]
    claims = [load_record(workspace / relative_path(path)) for path in args.claim]
    experiments = [load_record(workspace / relative_path(path)) for path in args.experiment]
    errors, summary = validate_evidence_graph(
        manifest,
        artifacts,
        claims,
        experiments,
        workspace=workspace,
        manifest_path=workspace / relative_path(args.manifest),
    )
    output = json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n"
    return (1, output + "\n".join(errors) + "\n", "") if errors else (0, output, "")


def _internal_independence(args: argparse.Namespace, workspace: Path) -> tuple[int, str, str]:
    if not args.review_record:
        return 2, "", "independent_or_human_closure requires --review-record\n"
    record = load_review_yaml(workspace / relative_path(args.review_record))
    ok, errors = validate_review_record(record)
    return (0, "review independence passed\n", "") if ok else (1, "\n".join(errors) + "\n", "")


def _internal_output_hash(args: argparse.Namespace, workspace: Path) -> tuple[int, str, str]:
    if not args.output_file:
        return 2, "", "output_hash requires at least one --output-file\n"
    hashes: list[str] = []
    for raw in args.output_file:
        path = workspace / relative_path(raw)
        if not path.is_file():
            return 1, "", f"missing output file: {raw}\n"
        hashes.append(f"{raw}: {sha256_file(path)}")
    return 0, "\n".join(hashes) + "\n", ""


def _internal_pdf_hash(args: argparse.Namespace, workspace: Path) -> tuple[int, str, str]:
    if not args.candidate_pdf:
        return 2, "", "pdf_hash requires --candidate-pdf\n"
    path = workspace / relative_path(args.candidate_pdf)
    if not path.is_file():
        return 1, "", f"missing candidate PDF: {args.candidate_pdf}\n"
    digest = sha256_file(path)
    if args.expected_pdf_sha256 and digest.lower() != args.expected_pdf_sha256.lower():
        return 1, f"actual SHA-256: {digest}\n", "candidate PDF hash mismatch\n"
    return 0, f"candidate PDF SHA-256: {digest}\n", ""


def _fixed_subprocess(check_id: str, args: argparse.Namespace) -> list[str] | None:
    if check_id in {"latex_fast_compile", "latex_compile"}:
        return ["make", "paper-ci"]
    if check_id == "code_tests":
        return ["make", "test"]
    if check_id == "citation_crossref_check":
        return [sys.executable, "scripts/qa_latex.py", "--paper-dir", "paper", "--build-dir", "paper/build"]
    if check_id == "pdf_static_qa":
        if not args.candidate_pdf:
            return None
        return ["sh", "writing/checks/check_pdf.sh", relative_path(args.candidate_pdf)]
    return None


INTERNAL_CHECKS: dict[str, Callable[[argparse.Namespace, Path], tuple[int, str, str]]] = {
    "basic_markdown_latex_syntax": lambda args, workspace: _internal_basic_syntax(workspace, args.changed_file),
    "file_allowlist": _internal_file_allowlist,
    "claim_experiment_binding": _internal_evidence_graph,
    "independent_or_human_closure": _internal_independence,
    "output_hash": _internal_output_hash,
    "pdf_hash": _internal_pdf_hash,
}


def run_checks(args: argparse.Namespace) -> dict:
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        raise ValueError(f"workspace does not exist: {workspace}")
    actual_base = _git_revision(workspace, args.base_ref)
    actual_head = _git_revision(workspace, args.head_ref)
    if actual_base is not None and actual_base != args.base_git_revision:
        raise ValueError("base_git_revision does not match base_ref")
    if actual_head is not None and actual_head != args.new_git_revision:
        raise ValueError("new_git_revision does not match head_ref")
    check_ids = list(dict.fromkeys(args.check_id))
    if not check_ids:
        check_ids = required_checks_for(
            args.change_level,
            args.changed_file,
            change_surfaces=args.change_surface,
            candidate_submission_pdf=bool(args.candidate_pdf),
        )
    unsafe = set(check_ids).difference(SAFE_CHECK_IDS)
    if unsafe:
        raise ValueError(f"unknown or unsafe check IDs: {sorted(unsafe)}")
    surfaces = list(args.change_surface)
    if not surfaces or set(surfaces).difference(CHANGE_SURFACES):
        raise ValueError("one or more valid --change-surface values are required")
    if args.change_level not in CHANGE_LEVELS:
        raise ValueError("invalid change level")
    evidence_root_rel = relative_path(args.evidence_root)
    evidence_root = workspace / evidence_root_rel
    started_at = now()
    check_results: list[dict] = []
    output_hashes: dict[str, str] = {}
    for index, check_id in enumerate(check_ids, start=1):
        check_started = now()
        implementation = CHECK_IMPLEMENTATION_STATUS[check_id]
        stdout = ""
        stderr = ""
        artifact_hashes: dict[str, str] = {}
        if implementation == "manual_required":
            code = None
            stdout = "manual evidence required; trusted runner did not claim this check passed\n"
        elif check_id in INTERNAL_CHECKS:
            code, stdout, stderr = INTERNAL_CHECKS[check_id](args, workspace)
        elif (argv := _fixed_subprocess(check_id, args)) is not None:
            code, stdout, stderr = _run_fixed_command(workspace, argv)
        else:
            code = 2
            stderr = f"check is not implemented by the trusted runner: {check_id}\n"
        stdout_path, stdout_hash = _write_log(workspace, evidence_root, f"{index:02d}_{check_id}.stdout.log", stdout)
        stderr_path, stderr_hash = _write_log(workspace, evidence_root, f"{index:02d}_{check_id}.stderr.log", stderr)
        for raw in args.output_file:
            path = workspace / relative_path(raw)
            if path.is_file():
                artifact_hashes[relative_path(raw)] = sha256_file(path)
                output_hashes[relative_path(raw)] = artifact_hashes[relative_path(raw)]
        if args.candidate_pdf and check_id == "pdf_hash":
            path = workspace / relative_path(args.candidate_pdf)
            if path.is_file():
                output_hashes[relative_path(args.candidate_pdf)] = sha256_file(path)
                artifact_hashes[relative_path(args.candidate_pdf)] = output_hashes[relative_path(args.candidate_pdf)]
        if implementation == "manual_required":
            status = "manual_required"
        elif code == 0:
            status = "passed"
        else:
            status = "failed"
        result = {
            "check_id": check_id,
            "status": status,
            "execution_kind": "trusted_runner",
            "executor": RUNNER_ID,
            "started_at": check_started,
            "finished_at": now(),
            "exit_code": code,
            "stdout_path": stdout_path,
            "stdout_sha256": stdout_hash,
            "stderr_path": stderr_path,
            "stderr_sha256": stderr_hash,
            "artifact_hashes": artifact_hashes,
            "attestation_path": None,
            "attestation_sha256": None,
            "notes": "fixed command or internal validator" if implementation == "implemented" else "human evidence must be attached",
        }
        check_results.append(result)
    finished_at = now()
    runner_path = workspace / SCRIPT_RELATIVE
    if not runner_path.is_file():
        raise FileNotFoundError(runner_path)
    record = {
        "record_type": "revision_validation_record",
        "revision_id": args.revision_id,
        "case_id": args.case_id,
        "approval_id": args.approval_id,
        "source_review_id": args.source_review_id,
        "finding_ids": list(args.finding_id),
        "base_git_revision": args.base_git_revision,
        "new_git_revision": args.new_git_revision,
        "change_level": args.change_level,
        "change_surfaces": surfaces,
        "changed_files": [relative_path(path) for path in args.changed_file],
        "evidence_root": evidence_root_rel,
        "runner_id": RUNNER_ID,
        "runner_version": RUNNER_VERSION,
        "runner_script": SCRIPT_RELATIVE,
        "runner_script_sha256": sha256_file(runner_path),
        "execution_started_at": started_at,
        "execution_finished_at": finished_at,
        "check_results": check_results,
        "output_hashes": output_hashes,
        "new_experiment_ids": list(args.new_experiment_id),
        "claim_status_updates": [],
        "closed_findings": [],
        "unresolved_findings": list(args.unresolved_finding),
        "validator": RUNNER_ID,
        "validation_status": "passed" if all(item["status"] == "passed" for item in check_results) else "failed",
    }
    output_path = Path(args.output_record)
    if not output_path.is_absolute():
        output_path = workspace / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    output_path.write_text(yaml.safe_dump(record, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--revision-id", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--change-level", choices=sorted(CHANGE_LEVELS), required=True)
    parser.add_argument("--change-surface", action="append", default=[], choices=sorted(CHANGE_SURFACES))
    parser.add_argument("--changed-file", action="append", default=[], required=True)
    parser.add_argument("--check-id", action="append", default=[])
    parser.add_argument("--output-record", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--base-git-revision", required=True)
    parser.add_argument("--new-git-revision", required=True)
    parser.add_argument("--approval-id")
    parser.add_argument("--source-review-id")
    parser.add_argument("--finding-id", action="append", default=[])
    parser.add_argument("--new-experiment-id", action="append", default=[])
    parser.add_argument("--unresolved-finding", action="append", default=[])
    parser.add_argument("--approval")
    parser.add_argument("--change-record")
    parser.add_argument("--review-record")
    parser.add_argument("--manifest")
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--claim", action="append", default=[])
    parser.add_argument("--experiment", action="append", default=[])
    parser.add_argument("--candidate-pdf")
    parser.add_argument("--expected-pdf-sha256")
    parser.add_argument("--output-file", action="append", default=[])
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--head-ref", default="HEAD")
    args = parser.parse_args()
    try:
        record = run_checks(args)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL trusted runner: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output_record": args.output_record, "validation_status": record["validation_status"], "checks": record["check_results"]}, ensure_ascii=False, indent=2))
    return 0 if record["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
