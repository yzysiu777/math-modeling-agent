import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.check_transition import validate_transition
from scripts.gate_contract import required_checks_for


def signoff_for(workspace: Path, revision: str = "a" * 40):
    pdf = workspace / "paper/build/main.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"valid pdf fixture")
    return {
        "record_type": "human_signoff",
        "signoff_id": "SIGN-1",
        "case_id": "CASE-1",
        "signer": "human owner",
        "signer_id": "human-owner",
        "signer_role": "human_owner",
        "actor": "human-owner",
        "signed_at": "2026-08-27T00:00:00+00:00",
        "git_revision": revision,
        "pdf_path": "paper/build/main.pdf",
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "approved_gates": [f"G{i}" for i in range(13)],
        "review_scope": ["all gates"],
        "checked_items": ["PDF"],
        "not_checked_items": ["none"],
        "expertise_limitations": ["none"],
        "open_limitations": [],
        "unresolved_findings": [],
        "decision": "approved",
    }


class StateMachineTests(unittest.TestCase):
    def test_normal_transition(self):
        ok, _ = validate_transition("intake", "routed", actor="task_router", evidence=["route.md"])
        self.assertTrue(ok)

    def test_gate_sequence_is_single_and_canonical(self):
        ok, _ = validate_transition("reviewed", "gate_passed", actor="orchestrator", evidence=["g7.md"])
        self.assertTrue(ok)
        ok, _ = validate_transition("gate_passed", "paper_ready", actor="paper_architect", evidence=["evidence-map.md"])
        self.assertTrue(ok)

    def test_requires_validated_human_freeze(self):
        ok, _ = validate_transition("pdf_qa_passed", "human_frozen", actor="codex", evidence=["qa.md"])
        self.assertFalse(ok)
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            signoff = signoff_for(workspace)
            ok, _ = validate_transition(
                "pdf_qa_passed", "human_frozen", actor="human-owner", evidence=["signoff.yml"],
                signoff=signoff, workspace=workspace, current_revision="a" * 40,
            )
            self.assertTrue(ok)

    def test_reviewer_cannot_self_approve(self):
        ok, _ = validate_transition(
            "results_verified", "reviewed", actor="codex", author="codex", evidence=["review.md"]
        )
        self.assertFalse(ok)

    def test_revision_loop_requires_evidence(self):
        ok, _ = validate_transition("gate_passed", "revision_pending", actor="codex", evidence=[])
        self.assertFalse(ok)
        ok, _ = validate_transition("gate_passed", "revision_pending", actor="codex", evidence=["revision REV-1"])
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "revision_pending", "impact_classified", actor="orchestrator",
            evidence=["impact.yml"], change_level="R1", change_surfaces=["paper_claim"],
        )
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "impact_classified", "targeted_validation", actor="reproducibility_engineer",
            evidence=["plan.json"], change_level="R1",
            required_checks=required_checks_for("R1", ["paper/results.tex"], change_surfaces=["paper_claim"]),
        )
        self.assertTrue(ok)

    def test_r0_revision_loop_restores_without_model_gate(self):
        checks = required_checks_for("R0", ["notes.md"], change_surfaces=["text_only"])
        ok, _ = validate_transition(
            "targeted_validation", "validation_passed", actor="validator",
            evidence=["passed.json"], validation_status="passed",
        )
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "validation_passed", "restore_affected_gate", actor="orchestrator",
            evidence=["no_gate_impact regression record"], change_level="R0",
            change_surfaces=["text_only"], affected_gates=[], gate_impact="no_gate_impact",
        )
        self.assertTrue(ok)
        self.assertTrue(checks)
        ok, _ = validate_transition(
            "restore_affected_gate", "gate_passed", actor="orchestrator",
            evidence=["restore regression record"],
        )
        self.assertTrue(ok)

    def test_non_r0_restore_requires_gate(self):
        ok, _ = validate_transition(
            "validation_passed", "restore_affected_gate", actor="orchestrator",
            evidence=["regression.md"], change_level="R1", change_surfaces=["paper_claim"],
            affected_gates=[], gate_impact="affected",
        )
        self.assertFalse(ok)

    def test_unsafe_check_id_is_rejected(self):
        ok, _ = validate_transition(
            "impact_classified", "targeted_validation", actor="validator",
            evidence=["plan.json"], change_level="R2", required_checks=["rm -rf /"]
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
