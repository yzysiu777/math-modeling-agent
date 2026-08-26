import unittest

from scripts.check_transition import validate_transition


class StateMachineTests(unittest.TestCase):
    def test_normal_transition(self):
        ok, _ = validate_transition("intake", "routed", actor="task_router", evidence=["route.md"])
        self.assertTrue(ok)

    def test_requires_human_freeze(self):
        ok, _ = validate_transition("pdf_qa_passed", "human_frozen", actor="codex", evidence=["qa.md"])
        self.assertFalse(ok)

    def test_revision_requires_approval(self):
        ok, _ = validate_transition("reviewed", "revision_approved", actor="human_owner", evidence=["review.md"])
        self.assertFalse(ok)

    def test_reviewer_cannot_self_approve(self):
        ok, _ = validate_transition("validated", "reviewed", actor="codex", author="codex", evidence=["review.md"])
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
