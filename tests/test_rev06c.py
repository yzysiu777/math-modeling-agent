from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.check_revision_closure import validate_revision_closure
from scripts.check_trusted_execution import result_digest
from scripts.git_contract import changed_files, file_sha256, validate_git_change_facts

try:
    from support_rev06c import build_real_r0_case
except ImportError:  # pragma: no cover - direct module invocation
    from tests.support_rev06c import build_real_r0_case


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(workspace: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=workspace, text=True).strip()


def _make_changed_repo() -> tuple[tempfile.TemporaryDirectory, Path, str, str]:
    holder = tempfile.TemporaryDirectory()
    workspace = Path(holder.name)
    (workspace / "notes.md").write_bytes(b"before\n")
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "MMAG REV-06C"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "notes.md"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=workspace, check=True)
    base = _git(workspace, "rev-parse", "HEAD")
    (workspace / "notes.md").write_bytes(b"after\n")
    subprocess.run(["git", "add", "notes.md"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "result"], cwd=workspace, check=True)
    result = _git(workspace, "rev-parse", "HEAD")
    return holder, workspace, base, result


class Rev06CGitFactTests(unittest.TestCase):
    def test_empty_actual_diff_rejects_claimed_changed_file(self):
        holder, workspace, base, _ = _make_changed_repo()
        try:
            errors = validate_git_change_facts(
                workspace,
                base,
                base,
                ["notes.md"],
                {"notes.md": _digest_bytes(b"before\n")},
                {"notes.md": _digest_bytes(b"before\n")},
            )
            self.assertTrue(any("actual Git diff is empty" in error for error in errors))
        finally:
            holder.cleanup()

    def test_recorded_file_must_equal_actual_file(self):
        holder, workspace, base, result = _make_changed_repo()
        try:
            errors = validate_git_change_facts(
                workspace,
                base,
                result,
                ["other.md"],
                {"other.md": None},
                {"other.md": _digest_bytes(b"other\n")},
            )
            self.assertTrue(any("actual and recorded changed files differ" in error for error in errors))
        finally:
            holder.cleanup()

    def test_before_and_after_hashes_are_repository_facts(self):
        holder, workspace, base, result = _make_changed_repo()
        try:
            errors = validate_git_change_facts(
                workspace,
                base,
                result,
                ["notes.md"],
                {"notes.md": "0" * 64},
                {"notes.md": "1" * 64},
            )
            self.assertTrue(any("before hash mismatch" in error for error in errors))
            self.assertTrue(any("after hash mismatch" in error for error in errors))
        finally:
            holder.cleanup()

    def test_added_and_deleted_files_use_null_on_absent_side(self):
        holder = tempfile.TemporaryDirectory()
        workspace = Path(holder.name)
        try:
            (workspace / "deleted.md").write_bytes(b"deleted\n")
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=workspace, check=True)
            subprocess.run(["git", "config", "user.name", "MMAG REV-06C"], cwd=workspace, check=True)
            subprocess.run(["git", "add", "deleted.md"], cwd=workspace, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=workspace, check=True)
            base = _git(workspace, "rev-parse", "HEAD")
            (workspace / "deleted.md").unlink()
            (workspace / "added.md").write_bytes(b"added\n")
            subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
            subprocess.run(["git", "commit", "-qm", "result"], cwd=workspace, check=True)
            result = _git(workspace, "rev-parse", "HEAD")
            actual = changed_files(workspace, base, result)
            self.assertEqual(actual, ["added.md", "deleted.md"])
            errors = validate_git_change_facts(
                workspace,
                base,
                result,
                actual,
                {
                    "added.md": None,
                    "deleted.md": file_sha256(workspace, base, "deleted.md"),
                },
                {
                    "added.md": file_sha256(workspace, result, "added.md"),
                    "deleted.md": None,
                },
            )
            self.assertEqual(errors, [])
            wrong = validate_git_change_facts(
                workspace,
                base,
                result,
                actual,
                {"added.md": "0" * 64, "deleted.md": file_sha256(workspace, base, "deleted.md")},
                {"added.md": file_sha256(workspace, result, "added.md"), "deleted.md": "0" * 64},
            )
            self.assertTrue(any("added file must be null" in error for error in wrong))
            self.assertTrue(any("deleted file must be null" in error for error in wrong))
        finally:
            holder.cleanup()


class Rev06CTrustedExecutionTests(unittest.TestCase):
    def test_modified_runner_cannot_self_generate_a_passing_record(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            impact, _, _ = build_real_r0_case(workspace)
            runner = workspace / "scripts/run_trusted_check.py"
            runner.write_text(runner.read_text(encoding="utf-8") + "\n# untrusted edit\n", encoding="utf-8")
            command = [
                sys.executable,
                str(runner),
                "--workspace", str(workspace),
                "--revision-id", impact["revision_id"],
                "--case-id", impact["case_id"],
                "--change-level", "R0",
                "--change-surface", "text_only",
                "--changed-file", "notes.md",
                "--output-record", "validation.yaml",
                "--evidence-root", "evidence/modified-runner",
                "--base-git-revision", impact["base_git_revision"],
                "--new-git-revision", impact["new_git_revision"],
                "--change-record", "impact.yaml",
                "--manifest", "manifest.yaml",
                "--base-ref", impact["base_git_revision"],
                "--head-ref", impact["new_git_revision"],
                "--closure-id", "CLOSURE-MODIFIED-RUNNER",
                "--executor-id", "executor-1",
                "--modifier-id", "modifier-1",
            ]
            process = subprocess.run(command, cwd=workspace, text=True, capture_output=True, check=False)
            self.assertEqual(process.returncode, 0)
            validation = yaml.safe_load((workspace / "validation.yaml").read_text(encoding="utf-8"))
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("protected base Git revision" in error for error in errors))

    def test_runner_id_and_self_hash_without_proof_are_not_enough(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            impact, validation, _ = build_real_r0_case(workspace)
            validation.pop("runner_context", None)
            for result in validation["check_results"]:
                result.pop("result_digest", None)
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("result_digest" in error for error in errors))
            self.assertTrue(any("runner context" in error for error in errors))

    def test_forged_passed_logs_with_a_matching_digest_fail_the_baseline_rerun(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            impact, validation, _ = build_real_r0_case(workspace)
            result = validation["check_results"][0]
            stdout_path = workspace / result["stdout_path"]
            stdout_path.write_text("forged passed output\n", encoding="utf-8")
            result["stdout_sha256"] = _digest_bytes(stdout_path.read_bytes())
            result["result_digest"] = result_digest(
                result["check_id"],
                result["status"],
                result["exit_code"],
                stdout_path.read_text(encoding="utf-8"),
                (workspace / result["stderr_path"]).read_text(encoding="utf-8"),
                result["artifact_hashes"],
            )
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("protected baseline result digest differs" in error for error in errors))
