import tempfile
import unittest
from pathlib import Path

from scripts.create_case import create_case
from scripts.experiment_board import validate_experiment_board
from scripts.check_spec import validate_case_specs
from scripts.check_case import check_case


VALID_BOARD = """# board

| 实验 ID | 路线 | 类型 | 要回答的问题/显式假设 | 预设判据 | 数据/实例范围 | 预算 | status | 结果与判定 | 是否继续 | 下一步 |
|---|---|---|---|---|---|---|---|---|---|---|
| EXP-001 | M-01 | probe | 缺测按无效值处理 | MAE < 1 | toy | 1 min | done | 判定：PASS，MAE=0.4 | yes | 写 Full SPEC |
"""


class CaseAndBoardTests(unittest.TestCase):
    def test_case_creation_uses_one_candidates_file_and_no_packet_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = create_case("demo-case", "hybrid", Path(tmp))
            self.assertTrue((case / "models/candidates.md").is_file())
            self.assertFalse((case / "models/comparison.md").exists())
            self.assertFalse((case / "reviews/packets").exists())
            self.assertIn("data_root:", (case / "input/README.md").read_text(encoding="utf-8"))
            reports = sorted((case / "reports").glob("stage-*.md"))
            self.assertEqual([path.name for path in reports], [f"stage-{stage:02d}.md" for stage in range(1, 8)])
            self.assertIn("待复核（不阻断）", reports[0].read_text(encoding="utf-8"))
            self.assertIn("待人工最终确认（阻断提交）", reports[-1].read_text(encoding="utf-8"))

    def test_compact_board_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "board.md"
            path.write_text(VALID_BOARD, encoding="utf-8")
            self.assertEqual(validate_experiment_board(path), [])

    def test_probe_requires_predetermined_assumption_and_criterion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "board.md"
            path.write_text(VALID_BOARD.replace("缺测按无效值处理", "待替换"), encoding="utf-8")
            self.assertTrue(any("显式假设" in item for item in validate_experiment_board(path)))

    def test_completed_probe_requires_explicit_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "board.md"
            path.write_text(VALID_BOARD.replace("判定：PASS，MAE=0.4", "MAE=0.4"), encoding="utf-8")
            self.assertTrue(any("PASS/FAIL" in item for item in validate_experiment_board(path)))

    def test_examples_follow_the_lightweight_board_and_spec_contract(self):
        root = Path(__file__).resolve().parents[1]
        for route in ("optimization", "data-analysis", "hybrid"):
            case = root / f"cases/examples/{route}"
            self.assertEqual(
                validate_experiment_board(case / "experiments/board.md"), []
            )
            self.assertEqual(validate_case_specs(case), [])
            self.assertFalse((case / "models/comparison.md").exists())
            self.assertEqual(list((case / "specs").glob("*-probe.md")), [])
            startup_codes = {finding.code for finding in check_case(case, "exploration").findings}
            self.assertNotIn("ROUTE_MISSING", startup_codes)
            self.assertNotIn("ROUTE_CONFIRMATION_REQUIRED", startup_codes)


if __name__ == "__main__":
    unittest.main()
