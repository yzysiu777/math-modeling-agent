import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_demos import run_all, validate_demo_case


class DemoTests(unittest.TestCase):
    def test_three_generic_demos_run_to_a_checked_baseline(self):
        results = run_all()
        self.assertEqual(len(results), 3)
        for script, code, stdout, stderr in results:
            self.assertEqual(code, 0, f"{script}: {stderr}")
            self.assertIn('"passed": true', stdout)
            json.loads(stdout)

    def test_demo_static_preflight_rejects_an_invalid_candidate_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.md"
            candidates.write_text(
                "## M-01\n- 方法族：same\n- 核心思想：a\n- 最便宜的证伪实验：b\n- 状态：candidate\n"
                "## M-02\n- 方法族：same\n- 核心思想：a\n- 最便宜的证伪实验：b\n- 状态：candidate\n"
                "## M-03\n- 方法族：same\n- 核心思想：a\n- 最便宜的证伪实验：b\n- 状态：candidate\n",
                encoding="utf-8",
            )
            board = root / "board.md"
            board.write_text(
                "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|\n"
                "| EXP-001 | M-01 | q | c | d | m | low | queued |  |  | 待当前实验后决定 |\n",
                encoding="utf-8",
            )
            errors = validate_demo_case(candidates, board)
        self.assertTrue(any("distinct method families" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
