import tempfile
import unittest
from pathlib import Path

from scripts.create_case import create_case
from scripts.experiment_board import validate_experiment_board
from scripts.model_pool import validate_candidate_pool


class CaseAndBoardTests(unittest.TestCase):
    def test_case_creation_needs_only_one_brief_and_creates_board(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("case-quickstart", "data_analysis", Path(directory))
            self.assertTrue((case / "case_brief.md").is_file())
            self.assertIn("`data_analysis`", (case / "case_brief.md").read_text(encoding="utf-8"))
            self.assertTrue((case / "models/candidates.md").is_file())
            self.assertEqual(validate_candidate_pool(case / "models/candidates.md"), [])
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

    def test_board_rejects_empty_required_fields_and_missing_status_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.md"
            path.write_text(
                "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|\n"
                "| EXP-001 | M-01 |  |  |  |  |  | queued |  |  |  |\n",
                encoding="utf-8",
            )
            errors = validate_experiment_board(path)
        self.assertTrue(any("empty required field: 要回答的问题" in error for error in errors))
        self.assertTrue(any("queued experiment EXP-001 needs a next experiment" in error for error in errors))

    def test_board_enforces_done_failed_and_skipped_content(self):
        header = "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
        separator = "|---|---|---|---|---|---|---|---|---|---|---|\n"
        base = "M-01 | 问题 | 配置 | 范围 | 指标 | low"
        with tempfile.TemporaryDirectory() as directory:
            done = Path(directory) / "done.md"
            done.write_text(
                header + separator + f"| EXP-001 | {base} | done |  | yes | 无/路线已确定 |\n",
                encoding="utf-8",
            )
            done_errors = validate_experiment_board(done)
            failed = Path(directory) / "failed.md"
            failed.write_text(
                header + separator + f"| EXP-001 | {base} | failed | solver timeout failure | no | 检查约束 |\n",
                encoding="utf-8",
            )
            failed_errors = validate_experiment_board(failed)
            skipped = Path(directory) / "skipped.md"
            skipped.write_text(
                header + separator + f"| EXP-001 | {base} | skipped | 因与主问题无关而跳过 |  |  |\n",
                encoding="utf-8",
            )
            skipped_errors = validate_experiment_board(skipped)
        self.assertTrue(any("done experiment EXP-001 needs a result summary" in error for error in done_errors))
        self.assertEqual(failed_errors, [])
        self.assertEqual(skipped_errors, [])


if __name__ == "__main__":
    unittest.main()
