import tempfile
import unittest
from pathlib import Path

from scripts.case_paths import (
    CROSS_QUESTION_BACKWARD_REFERENCE,
    reference_violation_code,
    resolve_in_case,
)


class CasePathTests(unittest.TestCase):
    def _case(self, root: Path) -> Path:
        case = root / "case-a"
        for question in ("q1", "q2", "q3"):
            (case / question / "outputs/data").mkdir(parents=True)
            (case / question / "outputs/data/x.csv").write_text(
                f"source,{question}\n", encoding="utf-8"
            )
        return case

    def test_q1_cannot_reference_q2_outputs_and_reports_stable_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = self._case(Path(tmp))
            reference = "q2/outputs/data/x.csv"
            self.assertEqual(
                reference_violation_code(reference, "q1"),
                CROSS_QUESTION_BACKWARD_REFERENCE,
            )
            self.assertIsNone(resolve_in_case(case, reference, "data", question="q1"))

    def test_q3_may_reference_q1_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = self._case(Path(tmp))
            reference = "q1/outputs/data/x.csv"
            self.assertIsNone(reference_violation_code(reference, "q3"))
            self.assertEqual(
                resolve_in_case(case, reference, "data", question="q3"),
                (case / reference).resolve(),
            )

    def test_unprefixed_evidence_is_relative_to_active_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = self._case(Path(tmp))
            self.assertEqual(
                resolve_in_case(case, "outputs/data/x.csv", "data", question=2),
                (case / "q2/outputs/data/x.csv").resolve(),
            )

    def test_kind_and_traversal_boundaries_still_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = self._case(Path(tmp))
            self.assertIsNone(resolve_in_case(case, "outputs/data/x.csv", "checks", question="q2"))
            self.assertIsNone(resolve_in_case(case, "../q1/outputs/data/x.csv", "data", question="q2"))


if __name__ == "__main__":
    unittest.main()
