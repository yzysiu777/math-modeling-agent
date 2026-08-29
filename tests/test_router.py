import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.router import route_problem


class RouterTests(unittest.TestCase):
    def test_optimization(self):
        result = route_problem("在容量约束下进行资源分配和调度，最小化总成本")
        self.assertEqual(result.route, "optimization")

    def test_data_analysis(self):
        result = route_problem("清洗样本数据，进行回归预测并报告置信区间")
        self.assertEqual(result.route, "data_analysis")

    def test_hybrid(self):
        result = route_problem("根据需求预测和特征数据，优化库存分配与补货决策")
        self.assertEqual(result.route, "hybrid")

    def test_insufficient(self):
        result = route_problem("请研究这个问题")
        self.assertEqual(result.route, "insufficient_information")

    def test_route_is_explicitly_advisory(self):
        result = route_problem("在容量约束下进行资源分配")
        self.assertEqual(result.suggested_route, result.route)
        self.assertTrue(result.requires_human_confirmation)
        self.assertIn("不是已确认路由", result.confirmation_message)

    def test_cli_exposes_suggested_route_and_confirmation_flag(self):
        root = Path(__file__).resolve().parents[1]
        process = subprocess.run(
            [sys.executable, str(root / "scripts/router.py"), "--text", "预测数据并优化资源分配"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0)
        payload = json.loads(process.stdout)
        self.assertEqual(payload["suggested_route"], payload["route"])
        self.assertTrue(payload["requires_human_confirmation"])
        self.assertIn("不是已确认路由", payload["confirmation_message"])


if __name__ == "__main__":
    unittest.main()
