import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.check_human_signoff import validate_human_signoff


class HumanSignoffTests(unittest.TestCase):
    def make_signoff(self, workspace: Path):
        pdf = workspace / "paper/main.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"pdf fixture")
        manifest = workspace / "manifest.yaml"
        manifest.write_text(
            "record_type: project_manifest\ncase_id: CASE-1\n"
            "owner:\n  name: owner\n  owner_id: owner-1\n  role: human_owner\n"
            "identity_allowlist:\n  - id: owner-1\n    role: human_owner\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=workspace, check=True)
        subprocess.run(["git", "config", "user.name", "MMAG Test"], cwd=workspace, check=True)
        subprocess.run(["git", "add", "manifest.yaml", "paper/main.pdf"], cwd=workspace, check=True)
        subprocess.run(["git", "commit", "-qm", "test fixture"], cwd=workspace, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip()
        return {
            "record_type": "human_signoff", "signoff_id": "SIGN-1", "case_id": "CASE-1",
            "signer": "owner", "signer_id": "owner-1", "signer_role": "human_owner", "actor": "owner-1",
            "project_manifest_path": "manifest.yaml", "project_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "signed_at": "2026-08-27T00:00:00+00:00", "git_revision": head,
            "pdf_path": "paper/main.pdf", "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "approved_gates": [f"G{i}" for i in range(13)], "review_scope": ["all"],
            "checked_items": ["pdf"], "not_checked_items": ["none"], "expertise_limitations": ["none"],
            "open_limitations": [], "unresolved_findings": [], "decision": "approved",
        }

    def test_valid_signoff(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = self.make_signoff(workspace)
            self.assertEqual(validate_human_signoff(signoff, actor="owner-1", current_revision=signoff["git_revision"], workspace=workspace, manifest={
                "record_type": "project_manifest", "case_id": "CASE-1",
                "owner": {"name": "owner", "owner_id": "owner-1", "role": "human_owner"},
                "identity_allowlist": [{"id": "owner-1", "role": "human_owner"}],
            }), [])

    def test_future_signed_at_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = self.make_signoff(workspace)
            signoff["signed_at"] = "2999-01-01T00:00:00+00:00"
            errors = validate_human_signoff(signoff, actor="owner-1", workspace=workspace)
            self.assertTrue(any("future" in error for error in errors))

    def test_timezone_less_signed_at_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = self.make_signoff(workspace)
            signoff["signed_at"] = "2026-08-28T12:00:00"
            errors = validate_human_signoff(signoff, actor="owner-1", workspace=workspace)
            self.assertTrue(any("timezone" in error for error in errors))

    def test_hash_or_open_p1_blocks_freeze(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = self.make_signoff(workspace)
            signoff["pdf_sha256"] = "0" * 64
            signoff["unresolved_findings"] = [{"finding_id": "P1-F-1", "severity": "P1", "statement": "open"}]
            errors = validate_human_signoff(signoff, actor="owner-1", current_revision=signoff["git_revision"], workspace=workspace, manifest={
                "record_type": "project_manifest", "case_id": "CASE-1",
                "owner": {"name": "owner", "owner_id": "owner-1", "role": "human_owner"},
                "identity_allowlist": [{"id": "owner-1", "role": "human_owner"}],
            })
            self.assertTrue(any("hash" in error or "P0/P1" in error for error in errors))

    def test_model_cannot_claim_human_owner(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = self.make_signoff(workspace)
            signoff["signer_id"] = signoff["actor"] = "codex-agent"
            errors = validate_human_signoff(signoff, actor="codex-agent", current_revision=signoff["git_revision"], workspace=workspace, manifest={
                "record_type": "project_manifest", "case_id": "CASE-1",
                "owner": {"name": "owner", "owner_id": "owner-1", "role": "human_owner"},
                "identity_allowlist": [{"id": "owner-1", "role": "human_owner"}],
            })
            self.assertTrue(any("frozen project owner" in error or "registered human identity" in error for error in errors))

    def test_supplied_revision_cannot_override_head(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = self.make_signoff(workspace)
            errors = validate_human_signoff(signoff, actor="owner-1", current_revision="a" * 40, workspace=workspace, manifest={
                "record_type": "project_manifest", "case_id": "CASE-1",
                "owner": {"name": "owner", "owner_id": "owner-1", "role": "human_owner"},
                "identity_allowlist": [{"id": "owner-1", "role": "human_owner"}],
            })
            self.assertTrue(any("does not match HEAD" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
