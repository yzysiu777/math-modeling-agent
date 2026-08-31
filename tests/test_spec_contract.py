import tempfile
import unittest
from pathlib import Path

from scripts.check_spec import validate_case_specs, validate_spec
from scripts.make_review_packet import _unique_target


BOARD = """| 实验 ID | 路线 | 类型 | 要回答的问题/显式假设 | 预设判据 | 数据/实例范围 | 预算 | status | 结果与判定 | 是否继续 | 下一步 |
|---|---|---|---|---|---|---|---|---|---|---|
{rows}
"""


def spec_text(probe: str = "EXP-001", recheck: str = "") -> str:
    return f"""---
spec_id: SPEC-Q1-M01
case_id: case-a
route_id: M-01
subproblem: Q1
method_family: graph
status: full
language: python
probe_exp_id: {probe}
probe_result: PASS
probe_waiver_reason: ""
reviewer_probe_recheck_exp_id: {recheck}
---
# Full
## 1. 目标与判据
目标及阈值。
## 2. 数学模型
变量目标约束。
## 3. 数据契约与显式假设
单位坐标时间缺测。
## 4. 算法与输出
算法入口输出。
## 5. 复算与遗留假设
约束目标复算。
"""


class SpecContractTests(unittest.TestCase):
    def test_five_section_full_spec_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SPEC-Q1-M01.md"
            path.write_text(spec_text(), encoding="utf-8")
            self.assertEqual(validate_spec(path), [])

    def test_probe_is_not_a_spec_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SPEC.md"
            path.write_text(spec_text().replace("status: full", "status: probe"), encoding="utf-8")
            self.assertTrue(any("只接受 status: full" in error for error in validate_spec(path)))

    def test_reviewer_probe_requires_completed_recheck_before_full_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case-a"
            (case / "specs").mkdir(parents=True)
            (case / "experiments").mkdir()
            (case / "specs/SPEC-Q1-M01.md").write_text(spec_text(), encoding="utf-8")
            rows = "| EXP-001 | M-01 | reviewer_probe | 结构是否可行 | PASS | toy | 1 min | done | 判定：PASS | yes | 复算 |"
            (case / "experiments/board.md").write_text(BOARD.format(rows=rows), encoding="utf-8")
            self.assertTrue(any("冻结 Full 前" in error for error in validate_case_specs(case)))

    def test_completed_recheck_closes_reviewer_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case-a"
            (case / "specs").mkdir(parents=True)
            (case / "experiments").mkdir()
            (case / "specs/SPEC-Q1-M01.md").write_text(spec_text(recheck="EXP-002"), encoding="utf-8")
            rows = "\n".join((
                "| EXP-001 | M-01 | reviewer_probe | 结构是否可行 | PASS | toy | 1 min | done | 判定：PASS | yes | 复算 |",
                "| EXP-002 | M-01 | recheck | 复算审核数字 | PASS | toy | 1 min | done | 判定：PASS | yes | 冻结 Full |",
            ))
            (case / "experiments/board.md").write_text(BOARD.format(rows=rows), encoding="utf-8")
            self.assertEqual(validate_case_specs(case), [])

    def test_review_card_targets_are_unique(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first, first_id = _unique_target(directory, "C1")
            first.write_text("x", encoding="utf-8")
            second, second_id = _unique_target(directory, "C1")
            self.assertNotEqual(first, second)
            self.assertNotEqual(first_id, second_id)

    def test_per_question_spec_uses_its_own_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case-a"
            (case / "q1/specs").mkdir(parents=True)
            (case / "q1/specs/SPEC-Q1-M01.md").write_text(spec_text(), encoding="utf-8")
            rows = "| EXP-001 | M-01 | probe | 结构是否可行 | PASS | toy | 1 min | done | 判定：PASS | yes | 写 Full |"
            (case / "q1/board.md").write_text(BOARD.format(rows=rows), encoding="utf-8")
            self.assertEqual(validate_case_specs(case), [])

    def test_per_question_spec_rejects_future_question_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case-a"
            (case / "q1/specs").mkdir(parents=True)
            text = spec_text().replace("算法入口输出。", "读取 q2/outputs/data/x.csv。")
            (case / "q1/specs/SPEC-Q1-M01.md").write_text(text, encoding="utf-8")
            rows = "| EXP-001 | M-01 | probe | 结构是否可行 | PASS | toy | 1 min | done | 判定：PASS | yes | 写 Full |"
            (case / "q1/board.md").write_text(BOARD.format(rows=rows), encoding="utf-8")
            errors = validate_case_specs(case)
            self.assertTrue(any("CROSS_QUESTION_BACKWARD_REFERENCE" in error for error in errors))

    def test_pending_probe_result_is_a_valid_full_spec_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SPEC-Q1-M01.md"
            path.write_text(
                spec_text().replace("probe_result: PASS", "probe_result: PENDING"),
                encoding="utf-8",
            )
            self.assertEqual(validate_spec(path), [])


if __name__ == "__main__":
    unittest.main()
