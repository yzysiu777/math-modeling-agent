import unittest

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


if __name__ == "__main__":
    unittest.main()
