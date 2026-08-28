import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_approved_revision import validate_revision_boundary
from scripts.create_review_bundle import create_bundle


class ReviewBundleTests(unittest.TestCase):
    def test_bundle_is_explicit_and_hashed(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "case"
            output = Path(temp) / "bundle"
            case.mkdir()
            (case / "problem.md").write_text("problem", encoding="utf-8")
            (case / "hidden_reasoning.md").write_text("do not include", encoding="utf-8")
            create_bundle(case, output, "C1", ["problem.md"], "REV-TEST-001")
            manifest = json.loads((output / "bundle_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["critical_node"], "C1")
            self.assertEqual(manifest["review_mode"], "blind")
            self.assertFalse(manifest["hidden_reasoning_included"])
            self.assertEqual([item["path"] for item in manifest["files"]], ["problem.md"])
            self.assertFalse((output / "hidden_reasoning.md").exists())


class RevisionBoundaryTests(unittest.TestCase):
    def test_empty_allowlist_fails_closed(self):
        approval = {
            "record_type": "approved_findings",
            "status": "approved",
            "allowed_files": [],
            "forbidden_files": ["input/"],
            "validation_check_ids": ["file_allowlist"],
        }
        impact = {
            "changed_files": ["paper/main.tex"],
            "before_hashes": {"paper/main.tex": "before"},
            "after_hashes": {"paper/main.tex": "after"},
        }
        with patch("scripts.check_approved_revision.changed_files", return_value=["paper/main.tex"]), patch(
            "scripts.check_approved_revision.git_file_sha256", side_effect=["before", "after"]
        ):
            errors = validate_revision_boundary(approval, impact)
        self.assertTrue(any("empty" in error for error in errors))

    def test_boundary_checks_before_and_after_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            manifest = workspace / "manifest.yaml"
            manifest.write_text(
                "record_type: project_manifest\ncase_id: CASE-1\n"
                "owner:\n  name: owner\n  owner_id: owner-1\n  role: human_owner\n"
                "identity_allowlist:\n  - id: owner-1\n    role: human_owner\n",
                encoding="utf-8",
            )
            approval = {
                "record_type": "approved_findings", "status": "approved", "case_id": "CASE-1", "approver_id": "owner-1", "approver_role": "human_owner",
                "approved_at": "2026-08-27T00:00:00+00:00", "expires_at": "2027-01-01T00:00:00+00:00",
                "allowed_files": ["paper/main.tex"], "forbidden_files": ["input/"], "validation_check_ids": ["latex_compile"],
                "project_manifest_path": "manifest.yaml", "project_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            }
            impact = {
                "case_id": "CASE-1", "changed_files": ["paper/main.tex"], "before_hashes": {"paper/main.tex": "a" * 64},
                "after_hashes": {"paper/main.tex": "b" * 64}, "executor_id": "executor-1", "modified_by": "modifier-1",
            }
            with patch("scripts.check_approved_revision.changed_files", return_value=["paper/main.tex"]), patch(
                "scripts.check_approved_revision.git_file_sha256", side_effect=["a" * 64, "b" * 64]
            ):
                errors = validate_revision_boundary(approval, impact, workspace=workspace)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
