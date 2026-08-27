import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.check_evidence_graph import validate_evidence_graph


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvidenceGraphTests(unittest.TestCase):
    def test_valid_hash_bound_claim_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            manifest_path = workspace / "manifest.yaml"
            manifest_path.write_text("record_type: project_manifest\ncase_id: CASE-1\n", encoding="utf-8")
            output = workspace / "results.json"
            output.write_text("{\"score\": 1}\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=workspace, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=workspace, check=True)
            subprocess.run(["git", "add", "manifest.yaml", "results.json"], cwd=workspace, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=workspace, check=True)
            code_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip()
            artifact = {
                "record_type": "artifact_record", "artifact_id": "ART-OUT", "case_id": "CASE-1",
                "path": "results.json", "kind": "table", "sha256": file_hash(output),
                "created_by": "executor", "status": "approved", "parents": [],
                "experiment_ids": ["EXP-1"], "claim_ids": ["CLM-1"], "paper_locators": ["paper/results.tex:10"],
            }
            claim = {
                "record_type": "claim_record", "claim_id": "CLM-1", "case_id": "CASE-1",
                "statement": "score is one", "claim_type": "result", "status": "supported",
                "importance": "P1", "provenance": [{"kind": "experiment", "locator": "EXP-1"}],
                "experiments": ["EXP-1"], "artifacts": ["ART-OUT"],
                "paper_locators": ["paper/results.tex:10"], "uncertainty": [],
                "last_changed_by": "executor", "last_changed_at": "2026-08-27T00:00:00+00:00",
            }
            experiment = {
                "record_type": "experiment_record", "experiment_id": "EXP-1", "case_id": "CASE-1",
                "question": "does it work?", "objective": "verify", "input_manifest_hash": file_hash(manifest_path),
                "code_revision": code_revision, "environment": {"os": "test", "python": "3", "packages": [], "solver": "none"},
                "command": "fixed test", "baseline_or_candidate": "candidate", "metrics": {},
                "outputs": [{"artifact_id": "ART-OUT", "path": "results.json", "sha256": file_hash(output)}],
                "review_status": "accepted",
            }
            errors, report = validate_evidence_graph(
                {"record_type": "project_manifest", "case_id": "CASE-1"},
                [artifact], [claim], [experiment], workspace=workspace, manifest_path=manifest_path,
            )
            self.assertEqual(errors, [])
            self.assertEqual(report["status"], "passed")

    def test_missing_output_hash_or_backlink_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            manifest_path = workspace / "manifest.yaml"
            manifest_path.write_text("manifest\n", encoding="utf-8")
            errors, _ = validate_evidence_graph(
                {"record_type": "project_manifest", "case_id": "CASE-1"},
                [{"record_type": "artifact_record", "artifact_id": "A", "case_id": "CASE-1", "path": "missing", "kind": "experiment", "sha256": "0" * 64}],
                [{"record_type": "claim_record", "claim_id": "C", "case_id": "CASE-1", "status": "supported", "importance": "P1", "experiments": ["E"], "artifacts": [], "paper_locators": [], "provenance": []}],
                [{"record_type": "experiment_record", "experiment_id": "E", "case_id": "CASE-1", "input_manifest_hash": "0" * 64, "code_revision": "a" * 40, "outputs": [{"artifact_id": "A", "path": "missing", "sha256": "0" * 64}]}],
                workspace=workspace, manifest_path=manifest_path,
            )
            self.assertTrue(any("does not exist" in error or "paper_locators" in error for error in errors))

    def test_fake_hex_revision_is_not_an_allowed_git_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            manifest_path = workspace / "manifest.yaml"
            manifest_path.write_text("record_type: project_manifest\ncase_id: CASE-1\n", encoding="utf-8")
            errors, _ = validate_evidence_graph(
                {"record_type": "project_manifest", "case_id": "CASE-1"}, [], [],
                [{"record_type": "experiment_record", "experiment_id": "E", "case_id": "CASE-1", "input_manifest_hash": file_hash(manifest_path), "code_revision": "a" * 40, "outputs": []}],
                workspace=workspace, manifest_path=manifest_path,
            )
            self.assertTrue(any("allowed reachable Git commit" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
