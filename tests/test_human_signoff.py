import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.check_human_signoff import validate_human_signoff


class HumanSignoffTests(unittest.TestCase):
    def make_signoff(self, workspace: Path):
        pdf = workspace / "paper/main.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"pdf fixture")
        return {
            "record_type": "human_signoff", "signoff_id": "SIGN-1", "case_id": "CASE-1",
            "signer": "owner", "signer_id": "owner-1", "signer_role": "human_owner", "actor": "owner-1",
            "signed_at": "2026-08-27T00:00:00+00:00", "git_revision": "a" * 40,
            "pdf_path": "paper/main.pdf", "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "approved_gates": [f"G{i}" for i in range(13)], "review_scope": ["all"],
            "checked_items": ["pdf"], "not_checked_items": ["none"], "expertise_limitations": ["none"],
            "open_limitations": [], "unresolved_findings": [], "decision": "approved",
        }

    def test_valid_signoff(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.assertEqual(validate_human_signoff(self.make_signoff(workspace), actor="owner-1", current_revision="a" * 40, workspace=workspace), [])

    def test_hash_or_open_p1_blocks_freeze(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = self.make_signoff(workspace)
            signoff["pdf_sha256"] = "0" * 64
            signoff["unresolved_findings"] = ["P1-F-1"]
            errors = validate_human_signoff(signoff, actor="owner-1", current_revision="a" * 40, workspace=workspace)
            self.assertTrue(any("hash" in error or "P0/P1" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
