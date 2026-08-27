import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.check_work_item import validate_work_item, validate_work_item_set
from scripts.gate_contract import required_checks_for


def valid_item(workspace: Path, **overrides):
    evidence = []
    item = {
        "record_type": "work_item", "work_item_id": "WI-1", "case_id": "CASE-1",
        "source_git_revision": "a" * 40, "objective": "update a note", "scope": ["update report"],
        "non_goals": ["do not change data"], "allowed_files": ["cases/CASE-1/coordination/report.md"],
        "affected_claims": [], "affected_experiments": [], "affected_gates": [],
        "required_checks": required_checks_for("R0", ["cases/CASE-1/coordination/report.md"], change_surfaces=["text_only"]),
        "change_level": "R0", "change_surfaces": ["text_only"], "required_review_nodes": [],
        "executor_id": "executor-1", "reviewer_id": "reviewer-1", "write_owner_id": "executor-1",
        "result_git_revision": "b" * 40, "test_evidence": [], "status": "accepted",
        "unresolved_items": [], "revision_id": "REV-1", "report_path": "cases/CASE-1/coordination/report.md",
        "human_decisions_required": [],
    }
    for index, check_id in enumerate(item["required_checks"]):
        path = workspace / f"evidence/{index}-{check_id}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("passed\n", encoding="utf-8")
        evidence.append({"check_id": check_id, "status": "passed", "evidence_path": str(path.relative_to(workspace)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    item["test_evidence"] = evidence
    item.update(overrides)
    return item


class WorkItemTests(unittest.TestCase):
    def test_accepted_item_does_not_imply_human_frozen(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), status="accepted")
            self.assertEqual(validate_work_item(item, workspace=Path(temp), source_ref="a" * 40, result_ref="b" * 40), [])
            self.assertNotIn("human_frozen", item)

    def test_self_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), reviewer_id="executor-1")
            self.assertTrue(any("self-review" in error for error in validate_work_item(item, workspace=Path(temp))))

    def test_source_or_result_revision_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp))
            errors = validate_work_item(item, workspace=Path(temp), source_ref="c" * 40, result_ref="d" * 40)
            self.assertTrue(any("source_git_revision" in error for error in errors))
            self.assertTrue(any("result_git_revision" in error for error in errors))

    def test_missing_required_check_and_unresolved_p1_block_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), test_evidence=[], unresolved_items=[{"id": "F-1", "severity": "P1", "statement": "open"}])
            errors = validate_work_item(item, workspace=Path(temp))
            self.assertTrue(any("cover every required check" in error for error in errors))
            self.assertTrue(any("unresolved P0/P1" in error for error in errors))

    def test_overlapping_active_scopes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            left = valid_item(Path(temp), work_item_id="WI-1", status="executing", allowed_files=["cases/CASE-1/coordination/"])
            right = valid_item(Path(temp), work_item_id="WI-2", status="review_ready", allowed_files=["cases/CASE-1/coordination/report.md"])
            errors = validate_work_item_set([left, right], workspace=Path(temp))
            self.assertTrue(any("overlapping active" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
