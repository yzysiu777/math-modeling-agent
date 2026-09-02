from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.check_case import check_case
from scripts.check_overfit import case_terms, find_leaks
from scripts.validate_workspace import PROBLEM_IDENTIFIERS, _retired_reference_errors


class OverfitGuardTests(unittest.TestCase):
    """工作台面向一类题目，不面向一道题。这条被指出过三次，两次是人工 grep 发现的。"""

    def _case(self, statement: str) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "input").mkdir(parents=True)
        (root / "input/题面全文.md").write_text(statement, encoding="utf-8")
        return root

    def test_a_problem_specific_term_in_guidance_is_reported(self):
        case = self._case("需要评估甲烷羽流的扩散。甲烷羽流的浓度随距离衰减。甲烷羽流是本题核心。\n")
        scratch = Path(tempfile.mkdtemp())
        try:
            doc = scratch / "prompts" / "writer.md"
            doc.parent.mkdir(parents=True)
            doc.write_text("举例：不要凭知识库断言甲烷羽流的扩散尺度。", encoding="utf-8")
            with mock.patch("scripts.check_overfit.ROOT", scratch), \
                 mock.patch("scripts.check_overfit.GUIDANCE_DIRS", ("prompts",)), \
                 mock.patch("scripts.check_overfit.GUIDANCE_ROOT_FILES", ()):
                leaks = find_leaks(case)
            self.assertTrue(any("甲烷羽流" in item for item in leaks))
        finally:
            shutil.rmtree(scratch)

    def test_generic_modelling_words_do_not_fire(self):
        case = self._case("建立模型分析数据。模型的数据要清洗。数据与模型都要检验。\n" * 3)
        terms = case_terms(case)
        for generic in ("模型", "数据", "分析", "检验"):
            self.assertNotIn(generic, terms)

    def test_cross_boundary_fragments_are_dropped(self):
        """「的结果」「个文件」这类跨词边界的碎片不是术语，报出来只会淹没真信号。"""
        case = self._case("观测的结果显示三个文件都是一个来源。的结果、个文件、是一个。\n" * 3)
        for fragment in ("的结果", "个文件", "是一个"):
            self.assertNotIn(fragment, case_terms(case))

    def test_the_workbench_itself_is_clean(self):
        """守卫对真实工作台跑一遍，应当没有命中。"""
        root = Path(__file__).resolve().parents[1]
        case = root / "cases/examples/optimization"
        if (case / "input/题面全文.md").is_file():
            self.assertEqual(find_leaks(case), [])


class ProblemIdentifierTests(unittest.TestCase):
    """题号、案例名和历年题路径出现在规范里没有正当理由，机械可判，直接报错。"""

    def test_identifiers_are_matched(self):
        for text in ("参考 2025 D 题", "见 2019F 附件", "在 往年真题/ 下", "cases/huawei-2025d"):
            with self.subTest(text=text):
                self.assertTrue(any(p.search(text) for p in PROBLEM_IDENTIFIERS))

    def test_generic_placeholders_pass(self):
        for text in ("cases/examples/optimization", "cases/contest-a", "cases/README.md",
                     "gmcmthesis 2025 版", "paper/official/2025/manifest.yaml"):
            with self.subTest(text=text):
                self.assertFalse(any(p.search(text) for p in PROBLEM_IDENTIFIERS))

    def test_workbench_names_no_problem(self):
        errors = [item for item in _retired_reference_errors() if "names a specific problem" in item]
        self.assertEqual(errors, [])


class SingleRouteReminderTests(unittest.TestCase):
    """发散六条、比较三条，最后只实现一条 —— 赛马从未真的发生过。"""

    def _case(self, spec_count: int) -> Path:
        from tests.test_case_check import make_question_case, question_review

        root = Path(tempfile.mkdtemp())
        passed = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        case = make_question_case(root, passed)
        question_review(case, nodes=("C1", "C2"))
        specs = case / "q1/specs"
        template = sorted(specs.glob("SPEC-*.md"))[0].read_text(encoding="utf-8")
        for index in range(2, spec_count + 1):
            (specs / f"SPEC-Q1-M-{index:02d}.md").write_text(
                template.replace("SPEC-Q1-M-01", f"SPEC-Q1-M-{index:02d}"), encoding="utf-8")
        return case

    def test_one_route_is_reminded(self):
        codes = {f.code for f in check_case(self._case(1), "model_selection").findings}
        self.assertIn("SINGLE_ROUTE", codes)

    def test_two_routes_pass(self):
        codes = {f.code for f in check_case(self._case(2), "model_selection").findings}
        self.assertNotIn("SINGLE_ROUTE", codes)

    def test_the_reminder_never_blocks(self):
        report = check_case(self._case(1), "model_selection")
        single = next(f for f in report.findings if f.code == "SINGLE_ROUTE")
        self.assertFalse(single.blocks)

    def test_exploration_does_not_nag_before_specs_exist(self):
        codes = {f.code for f in check_case(self._case(1), "exploration").findings}
        self.assertNotIn("SINGLE_ROUTE", codes)


if __name__ == "__main__":
    unittest.main()
