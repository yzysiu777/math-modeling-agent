import tempfile
import unittest
from pathlib import Path

from scripts.check_case import check_case


def make_case(root: Path, case_id: str = "case-a", *, complete_startup: bool = True) -> Path:
    case = root / case_id
    for relative in ("input", "reviews", "models", "experiments/outputs/checks", "paper"):
        (case / relative).mkdir(parents=True, exist_ok=True)
    (case / "checkpoint.yaml").write_text(
        f"""case_id: {case_id}
stage: 1
route:
  value: optimization
  decided_by: modeler
  confirmed_by_human: {'true' if complete_startup else 'false'}
  note: test
reviews: {{C1: pending, C2: pending, C3: pending}}
human_block: ""
deterministic_risks:
  infeasible: false
  objective_mismatch: false
  leakage: false
  split_overlap: false
""", encoding="utf-8"
    )
    (case / "models/candidates.md").write_text("# candidates\n", encoding="utf-8")
    if complete_startup:
        (case / "input/problem.md").write_text("题面", encoding="utf-8")
        (case / "case_brief.md").write_text(
            "# brief\n- 用户真正要回答什么：最小化成本\n"
            "| Q1 | 分配 | 成本 | 方案 | 无 |\n- 数据文件和粒度：玩具实例\n",
            encoding="utf-8",
        )
    return case


def review(case: Path, node: str, decision: str = "GO", rejection: str = "", signback: str = "") -> None:
    (case / "reviews" / f"{node}_done.md").write_text(
        f"""# {node}
Node decision: {decision}
Rejected finding: {rejection}
Reviewer sign-back: {signback}
""", encoding="utf-8"
    )


class CaseCheckTests(unittest.TestCase):
    def test_exploration_moves_without_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_case(make_case(Path(tmp)), "exploration")
            self.assertFalse(report.blocked)

    def test_blank_startup_is_reminded_during_exploration(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_case(make_case(Path(tmp), complete_startup=False), "exploration")
            self.assertFalse(report.blocked)
            self.assertEqual(
                {finding.code for finding in report.findings},
                {"INPUT_MATERIAL_MISSING", "CASE_BRIEF_INCOMPLETE", "ROUTE_CONFIRMATION_REQUIRED"},
            )

    def test_historical_prose_data_root_counts_as_input_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = make_case(root)
            (case / "input/problem.md").unlink()
            data_root = root / "随题数据" / "第一题"
            data_root.mkdir(parents=True)
            (case / "input/README.md").write_text(
                f"数据根（只读）：`{data_root}/`\n", encoding="utf-8"
            )
            codes = {finding.code for finding in check_case(case, "exploration").findings}
            self.assertNotIn("INPUT_MATERIAL_MISSING", codes)

    def test_route_confirmation_blocks_model_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp), complete_startup=False)
            (case / "input/problem.md").write_text("题面", encoding="utf-8")
            (case / "case_brief.md").write_text(
                "- 用户真正要回答什么：最小化成本\n"
                "| Q1 | 分配 | 成本 | 方案 | 无 |\n- 数据文件和粒度：玩具实例\n",
                encoding="utf-8",
            )
            review(case, "C1")
            review(case, "C2")
            report = check_case(case, "model_selection")
            self.assertIn("ROUTE_CONFIRMATION_REQUIRED", {finding.code for finding in report.findings if finding.blocks})

    def test_model_selection_requires_c1_and_c2_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            report = check_case(case, "model_selection")
            self.assertTrue(report.blocked)
            self.assertEqual({f.code for f in report.findings if f.blocks}, {"C1_REQUIRED", "C2_REQUIRED"})

    def test_go_cards_allow_model_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1")
            review(case, "C2", "GO_WITH_FIXES")
            self.assertFalse(check_case(case, "model_selection").blocked)

    def test_stop_blocks_but_is_owned_by_ai_unless_human_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1", "STOP")
            review(case, "C2")
            finding = next(f for f in check_case(case, "model_selection").findings if f.code == "C1_STOP")
            self.assertEqual(finding.owner, "ORCHESTRATOR")

    def test_rejecting_finding_requires_reviewer_signback(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1", rejection="P1-1")
            review(case, "C2")
            self.assertTrue(check_case(case, "model_selection").blocked)
            review(case, "C1", rejection="P1-1", signback="ACCEPT_REJECTION")
            self.assertFalse(check_case(case, "model_selection").blocked)

    def test_reviewer_can_reject_producer_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1", rejection="P1-1", signback="REJECT_REJECTION")
            review(case, "C2")
            self.assertTrue(check_case(case, "model_selection").blocked)

    def test_metadata_is_not_treated_as_identity_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1")
            review(case, "C2")
            self.assertFalse(check_case(case, "model_selection").blocked)

    def test_human_block_is_the_only_early_human_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            text = (case / "checkpoint.yaml").read_text(encoding="utf-8")
            (case / "checkpoint.yaml").write_text(
                text.replace('human_block: ""', 'human_block: "官方文字与官方数据冲突，改变可用数据范围"'),
                encoding="utf-8",
            )
            finding = next(f for f in check_case(case, "exploration").findings if f.code == "HUMAN_ONLY_BLOCK")
            self.assertEqual(finding.owner, "HUMAN")

    def test_paper_claims_requires_c3(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1")
            review(case, "C2")
            self.assertIn("C3_REQUIRED", {f.code for f in check_case(case, "paper_claims").findings})


if __name__ == "__main__":
    unittest.main()
