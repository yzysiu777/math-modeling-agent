import unittest

from scripts.check_transition import validate_transition


class StateMachineTests(unittest.TestCase):
    def test_normal_transition(self):
        ok, _ = validate_transition("intake", "routed", actor="task_router", evidence=["route.md"])
        self.assertTrue(ok)

    def test_gate_sequence_is_single_and_canonical(self):
        ok, _ = validate_transition("reviewed", "gate_passed", actor="orchestrator", evidence=["g7.md"])
        self.assertTrue(ok)
        ok, _ = validate_transition("gate_passed", "paper_ready", actor="paper_architect", evidence=["evidence-map.md"])
        self.assertTrue(ok)

    def test_requires_human_freeze(self):
        ok, _ = validate_transition("pdf_qa_passed", "human_frozen", actor="codex", evidence=["qa.md"])
        self.assertFalse(ok)
        ok, _ = validate_transition("pdf_qa_passed", "human_frozen", actor="human_owner", evidence=["signoff.yml"])
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
            evidence=["impact.yml"], change_level="R1",
        )
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "impact_classified", "targeted_validation", actor="reproducibility_engineer",
            evidence=["plan.json"], change_level="R1", required_checks=["latex_compile"],
        )
        self.assertTrue(ok)

    def test_revision_outcomes_and_restore(self):
        ok, _ = validate_transition(
            "targeted_validation", "validation_failed", actor="validator",
            evidence=["failed.log"], validation_status="failed",
        )
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "validation_failed", "targeted_validation", actor="validator",
            evidence=["retry-plan.json"], required_checks=["file_allowlist"],
        )
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "targeted_validation", "validation_passed", actor="validator",
            evidence=["passed.json"], validation_status="passed",
        )
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "validation_passed", "restore_affected_gate", actor="orchestrator",
            evidence=["regression.md"], change_level="R0", affected_gates=["G11"],
        )
        self.assertTrue(ok)
        ok, _ = validate_transition(
            "restore_affected_gate", "gate_passed", actor="orchestrator",
            evidence=["restore regression record"],
        )
        self.assertTrue(ok)

    def test_r0_cannot_restore_model_gate(self):
        ok, _ = validate_transition(
            "validation_passed", "restore_affected_gate", actor="orchestrator",
            evidence=["regression.md"], change_level="R0", affected_gates=["G4"],
        )
        self.assertFalse(ok)

    def test_unsafe_check_id_is_rejected(self):
        ok, _ = validate_transition(
            "impact_classified", "targeted_validation", actor="validator",
            evidence=["plan.json"], change_level="R2", required_checks=["rm -rf /"],
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
