import tempfile
import unittest
from pathlib import Path

from scripts.create_case import create_case
from scripts.experiment_board import validate_experiment_board


class CaseAndBoardTests(unittest.TestCase):
    def test_case_creation_needs_only_one_brief_and_creates_board(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("case-quickstart", "data_analysis", Path(directory))
            self.assertTrue((case / "case_brief.md").is_file())
            self.assertIn("`data_analysis`", (case / "case_brief.md").read_text(encoding="utf-8"))
            self.assertTrue((case / "models/candidates.md").is_file())
            self.assertEqual(validate_experiment_board(case / "experiments/board.md"), [])
            with self.assertRaises(FileExistsError):
                create_case("case-quickstart", "data_analysis", Path(directory))

    def test_board_rejects_unknown_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.md"
            path.write_text(
                "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|\n"
                "| EXP-001 | M-01 | q | small | toy | score | low | unknown |  |  |  |\n",
                encoding="utf-8",
            )
            errors = validate_experiment_board(path)
            self.assertTrue(any("invalid experiment status" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
