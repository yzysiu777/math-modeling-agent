import argparse
import hashlib
import tempfile
import unittest
from pathlib import Path
import shutil

from scripts.run_trusted_check import RUNNER_VERSION, run_checks


def runner_args(workspace: Path, check_ids):
    return argparse.Namespace(
        workspace=workspace,
        revision_id="REV-RUNNER-1",
        case_id="CASE-RUNNER-1",
        change_level="R0",
        change_surface=["text_only"],
        changed_file=["notes.md"],
        check_id=list(check_ids),
        output_record=str(workspace / "validation.yaml"),
        evidence_root="evidence/REV-RUNNER-1",
        base_git_revision="a" * 40,
        new_git_revision="b" * 40,
        approval_id=None,
        source_review_id=None,
        finding_id=[],
        new_experiment_id=[],
        unresolved_finding=[],
        approval=None,
        change_record=None,
        review_record=None,
        manifest=None,
        artifact=[],
        claim=[],
        experiment=[],
        candidate_pdf=None,
        expected_pdf_sha256=None,
        output_file=[],
        base_ref="main",
        head_ref="HEAD",
    )


class TrustedRunnerTests(unittest.TestCase):
    def test_automatic_pdf_hash_passes_with_recorded_output_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            shutil.copy2(Path(__file__).parents[1] / "scripts/run_trusted_check.py", workspace / "scripts/run_trusted_check.py")
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"candidate pdf")
            args = runner_args(workspace, ["pdf_hash"])
            args.change_level = "R1"
            args.change_surface = ["candidate_pdf"]
            args.candidate_pdf = "candidate.pdf"
            args.expected_pdf_sha256 = hashlib.sha256(pdf.read_bytes()).hexdigest()
            record = run_checks(args)
            self.assertEqual(record["validation_status"], "passed")
            self.assertEqual(record["check_results"][0]["status"], "passed")
            self.assertIn("candidate.pdf", record["output_hashes"])

    def test_automatic_pdf_hash_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            shutil.copy2(Path(__file__).parents[1] / "scripts/run_trusted_check.py", workspace / "scripts/run_trusted_check.py")
            (workspace / "candidate.pdf").write_bytes(b"candidate pdf")
            args = runner_args(workspace, ["pdf_hash"])
            args.change_level = "R1"
            args.change_surface = ["candidate_pdf"]
            args.candidate_pdf = "candidate.pdf"
            args.expected_pdf_sha256 = "0" * 64
            record = run_checks(args)
            self.assertEqual(record["validation_status"], "failed")
            self.assertEqual(record["check_results"][0]["status"], "failed")

    def test_manual_check_is_never_reported_as_passed(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            source_runner = Path(__file__).parents[1] / "scripts/run_trusted_check.py"
            shutil.copy2(source_runner, workspace / "scripts/run_trusted_check.py")
            record = run_checks(runner_args(workspace, ["small_case_check"]))
            self.assertEqual(record["runner_version"], RUNNER_VERSION)
            self.assertEqual(record["check_results"][0]["status"], "manual_required")
            self.assertEqual(record["validation_status"], "failed")
            self.assertTrue((workspace / record["check_results"][0]["stdout_path"]).is_file())

    def test_unknown_check_id_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            shutil.copy2(Path(__file__).parents[1] / "scripts/run_trusted_check.py", workspace / "scripts/run_trusted_check.py")
            with self.assertRaises(ValueError):
                run_checks(runner_args(workspace, ["rm -rf /"]))

    def test_command_catalog_does_not_accept_yaml_command_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            shutil.copy2(Path(__file__).parents[1] / "scripts/run_trusted_check.py", workspace / "scripts/run_trusted_check.py")
            args = runner_args(workspace, ["code_tests"])
            args.command = "echo compromised"
            record = run_checks(runner_args(workspace, ["small_case_check"]))
            self.assertNotIn("command", record)


if __name__ == "__main__":
    unittest.main()
