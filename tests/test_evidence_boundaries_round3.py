"""MMAG-006 第三轮：符号链接边界、来源实验唯一性、报告归属与测试副作用。

命名以 `test_r3_p1_<n>_` / `test_r3_p2_1_` 开头，对应 Reviewer 第三轮交接文档的编号。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.check_case import check_case
from scripts.claim_evidence import parse_source_experiment, validate_check_report
from scripts.create_case import create_case
from scripts.make_review_packet import build_packet


ROOT = Path(__file__).resolve().parents[1]
BOARD = (
    "# 实验赛马板\n\n"
    "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|\n"
    "| EXP-001 | M-01 | 是否可行 | toy | toy | 成本 | low | done | 判定：PASS | yes | 下一步 |\n"
)
HEADER = (
    "| Claim ID | 论文位置 | 主张原文 | 强度 | 来源 EXP-ID | 数据文件 | 图/表 ID | 复算报告 | 状态 |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)


class Round3Tests(unittest.TestCase):
    # ------------------------------------------------------------------ 夹具

    def case(self, directory, case_id="r3case"):
        case = create_case(case_id, "optimization", Path(directory))
        path = case / "checkpoint.yaml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        payload["routing"].update({"confirmed": True, "confirmed_route": "optimization",
                                   "confirmed_by": "队长", "note": "已对照题面核实"})
        payload["reviews"]["C1"] = "not_needed"
        payload["review_notes"]["C1"] = "题意由题面直接给定"
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        (case / "models/comparison.md").write_text(
            "# 比较\n\n当前 Champion：M-01\n当前 Challenger：M-02\n", encoding="utf-8")
        (case / "experiments/board.md").write_text(BOARD, encoding="utf-8")
        (case / "reviews/C3.md").write_text(
            f"# C3\n\nReview ID: r-C3\nCase ID: {case.name}\n"
            "Reviewer provider: human_specialist\nReviewer model: 人工专家\n"
            "Review session: fresh\nSaw main conversation: false\nCritical node: C3\n\n"
            "结论：PASS_WITH_LIMITATIONS\nWhat was checked: 约束\nWhat was not checked: 大规模\n",
            encoding="utf-8")
        return case

    def evidence(self, case, exp="EXP-001", report_payload=None, data_name=None):
        outputs = case / "experiments/outputs"
        (outputs / "data").mkdir(parents=True, exist_ok=True)
        (outputs / (data_name or f"data/{exp}.csv")).write_text("a,b\n1,2\n", encoding="utf-8")
        (outputs / "checks").mkdir(parents=True, exist_ok=True)
        (outputs / f"checks/{exp}.json").write_text(json.dumps(
            report_payload if report_payload is not None else
            {"exp_id": exp, "checks": [{"name": "cap", "kind": "constraint", "passed": True}]}),
            encoding="utf-8")
        (outputs / "figures").mkdir(parents=True, exist_ok=True)
        (outputs / "figures/manifest.md").write_text(
            "# 图表清单\n\n| FIG-ID | 来源 EXP-ID | 生成脚本 | 数据文件 | 图题草稿 | 论文位置 | 状态 |\n"
            "|---|---|---|---|---|---|---|\n"
            f"| FIG-001 | {exp} | plot.py | d.csv | 图题 | 第 4 章 | final |\n", encoding="utf-8")

    def claim(self, case, exp="EXP-001", data="outputs/data/EXP-001.csv",
              figure="FIG-001", report="outputs/checks/EXP-001.json", status="verified"):
        (case / "paper/claim_map.md").write_text(
            "# 溯源\n\n" + HEADER +
            f"| CLM-001 | 摘要 | 全部算例均可行 | 可行解 | {exp} | {data} | {figure} | {report} | {status} |\n",
            encoding="utf-8")

    def claim_findings(self, report):
        return [f for f in report.findings
                if f.code.startswith("CLAIM") or "claim_map" in f.reason]

    # ---------------------------------------- P1-1 C1 input/ 符号链接边界

    def test_r3_p1_1_statement_symlink_out_of_the_case_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "secret.txt").write_text("TOP-SECRET-OUTSIDE", encoding="utf-8")
            case = self.case(root / "cases")
            os.symlink(root / "secret.txt", case / "input/题面.md")
            packet = build_packet(case, "C1")
        self.assertNotIn("TOP-SECRET-OUTSIDE", packet)
        self.assertIn("packet_complete: false", packet)
        self.assertIn("指向案例目录之外", packet)

    def test_r3_p1_1_attachment_symlink_out_of_the_case_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside.csv").write_text("secret_col\n42\n", encoding="utf-8")
            case = self.case(root / "cases")
            (case / "input/题面.md").write_text("# 原题\n\n正文在此。\n", encoding="utf-8")
            os.symlink(root / "outside.csv", case / "input/data.csv")
            packet = build_packet(case, "C1")
        self.assertNotIn("secret_col", packet)
        self.assertIn("packet_complete: false", packet)

    def test_r3_p1_1_legitimate_statement_and_attachment_still_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            (case / "input/题面.md").write_text("# 原题\n\n两个服务点三个需求点。\n", encoding="utf-8")
            (case / "input/nodes.csv").write_text("id,x\n1,0\n", encoding="utf-8")
            packet = build_packet(case, "C1")
        self.assertIn("packet_complete: true", packet)
        self.assertIn("两个服务点三个需求点", packet)
        self.assertIn("数据附件", packet)

    # ------------------------------- P1-2 来源 EXP-ID 只从来源列读且必须唯一

    def test_r3_p1_2_source_id_is_not_masked_by_a_data_filename(self):
        """来源列 EXP-999（板上没有），数据文件名含板上的 EXP-001。"""

        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            self.evidence(case, exp="EXP-999")
            self.claim(case, exp="EXP-999", data="outputs/data/EXP-001.csv",
                       report="outputs/checks/EXP-999.json")
            claiming = check_case(case, "paper_claims")
            final = check_case(case, "final")
        hit = [f for f in claiming.findings if "无法追溯到实验板" in f.reason]
        self.assertTrue(hit)
        self.assertIn("EXP-999", hit[0].reason)
        self.assertNotIn("EXP-001", hit[0].reason)
        self.assertTrue(hit[0].blocks)
        self.assertEqual(claiming.exit_code, 1)
        self.assertEqual(final.exit_code, 1)

    def test_r3_p1_2_two_ids_in_the_source_cell_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            self.claim(case, exp="EXP-001 EXP-999")
            claiming = check_case(case, "paper_claims")
        hit = self.claim_findings(claiming)
        self.assertTrue(any("必须唯一" in f.reason for f in hit))
        self.assertTrue(all(f.blocks for f in hit))

    def test_r3_p1_2_source_cell_with_extra_text_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            self.claim(case, exp="EXP-001（见附录 A）")
            claiming = check_case(case, "paper_claims")
        self.assertTrue(any("无法唯一解析" in f.reason for f in self.claim_findings(claiming)))
        self.assertEqual(claiming.exit_code, 1)

    def test_r3_p1_2_filename_fragment_is_not_a_canonical_id(self):
        """`EXP-001_solution` 是文件名片段，不是实验 ID。"""

        self.assertFalse(parse_source_experiment("EXP-001_solution").ok)
        self.assertEqual(parse_source_experiment("EXP-001").exp_id, "EXP-001")
        self.assertEqual(parse_source_experiment(" `exp-opt-002` ").exp_id, "EXP-OPT-002")

    def test_r3_p1_2_single_valid_id_with_full_evidence_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            self.claim(case)
            claiming = check_case(case, "paper_claims")
        self.assertFalse(self.claim_findings(claiming))
        self.assertEqual(claiming.exit_code, 0)

    # ------------------------------------- P1-3 复算报告 exp_id 必填且一致

    def test_r3_p1_3_report_without_exp_id_blocks_at_both_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case, report_payload={"checks": [{"name": "ok", "passed": True}]})
            self.claim(case)
            claiming = check_case(case, "paper_claims")
            final = check_case(case, "final")
        hit = self.claim_findings(claiming)
        self.assertTrue(any("缺少 exp_id" in f.reason for f in hit))
        self.assertTrue(all(f.blocks for f in hit))
        self.assertEqual(claiming.exit_code, 1)
        self.assertEqual(final.exit_code, 1)

    def test_r3_p1_3_c3_packet_marks_a_report_without_exp_id_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case, report_payload={"checks": [{"name": "ok", "passed": True}]})
            self.claim(case)
            packet = build_packet(case, "C3")
        self.assertIn("packet_complete: false", packet)
        self.assertIn("缺少 exp_id", packet)

    def test_r3_p1_3_report_with_multiple_or_malformed_exp_id_is_rejected(self):
        for label, exp_value in (("两个 ID", "EXP-001 EXP-002"),
                                 ("附加文本", "EXP-001 (rerun)"),
                                 ("空白", "   ")):
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.case(directory)
                    self.evidence(case, report_payload={
                        "exp_id": exp_value,
                        "checks": [{"name": "ok", "kind": "constraint", "passed": True}]})
                    self.claim(case)
                    claiming = check_case(case, "paper_claims")
                self.assertTrue(self.claim_findings(claiming), label)
                self.assertTrue(all(f.blocks for f in self.claim_findings(claiming)), label)

    def test_r3_p1_3_matching_report_still_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            self.claim(case)
            packet = build_packet(case, "C3")
        self.assertIn("packet_complete: true", packet)

    def test_r3_p1_3_checker_and_packet_share_one_report_contract(self):
        """两处必须走同一个校验函数，避免再次漂移。"""

        import scripts.check_case as check_case_module
        import scripts.make_review_packet as packet_module

        self.assertIs(check_case_module.validate_check_report, validate_check_report)
        self.assertIs(packet_module.validate_check_report, validate_check_report)
        self.assertFalse(hasattr(check_case_module, "_report_verdict"))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "r.json"
            path.write_text(json.dumps({"checks": [{"name": "x", "passed": True}]}), encoding="utf-8")
            self.assertIn("缺少 exp_id", validate_check_report(path, "EXP-001").problem)

    # --------------------- P1-4 已填 Claim 缺证据字段在两个阶段都阻断

    def test_r3_p1_4_missing_evidence_fields_block_at_both_stages(self):
        for label, kwargs in (("空数据文件", dict(data="")),
                              ("空来源 EXP-ID", dict(exp="")),
                              ("空复算报告", dict(report=""))):
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.case(directory)
                    self.evidence(case)
                    self.claim(case, **kwargs)
                    claiming = check_case(case, "paper_claims")
                    final = check_case(case, "final")
                hit = self.claim_findings(claiming)
                self.assertTrue(hit, label)
                self.assertTrue(all(f.blocks for f in hit), label)
                self.assertEqual(claiming.exit_code, 1, label)
                self.assertEqual(final.exit_code, 1, label)

    def test_r3_p1_4_empty_claim_map_still_only_reminds(self):
        """论文骨架没开始仍然只是进度问题，不恢复重型门禁。"""

        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            claiming = check_case(case, "paper_claims")
        hit = self.claim_findings(claiming)
        self.assertTrue(hit)
        self.assertFalse(any(f.blocks for f in hit))
        self.assertEqual(claiming.exit_code, 0)

    def test_r3_p1_4_writing_fields_stay_lightweight(self):
        """主张原文/强度未写完只提醒，不与证据缺失同级。"""

        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            (case / "paper/claim_map.md").write_text(
                "# 溯源\n\n" + HEADER +
                "| CLM-001 | 摘要 | 待填写 | 待填写 | EXP-001 | outputs/data/EXP-001.csv | "
                "FIG-001 | outputs/checks/EXP-001.json | draft |\n", encoding="utf-8")
            claiming = check_case(case, "paper_claims")
        incomplete = [f for f in claiming.findings if f.code == "CLAIM_MAP_INCOMPLETE"]
        self.assertTrue(incomplete)
        self.assertFalse(any(f.blocks for f in incomplete))


class WorkingTreeSideEffectTests(unittest.TestCase):
    """P2-1：测试与演示不得改写已跟踪的结果文件。"""

    def test_r3_p2_1_demo_keeps_timing_out_of_tracked_results(self):
        metrics = json.loads(
            (ROOT / "cases/examples/optimization/experiments/outputs/data/EXP-OPT-002_metrics.json")
            .read_text(encoding="utf-8"))
        self.assertNotIn("runtime_sec", metrics)
        self.assertIn("instances", metrics)
        self.assertEqual(metrics["exp_id"], "EXP-OPT-002")

    def test_r3_p2_1_run_logs_are_ignored_by_git(self):
        result = subprocess.run(
            ["git", "check-ignore", "-q",
             "cases/examples/optimization/experiments/outputs/logs/EXP-OPT-002_runtime.json"],
            cwd=ROOT, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, "运行日志必须被 gitignore")

    def test_r3_p2_1_demos_leave_no_tracked_diff(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout
        subprocess.run([sys.executable, "scripts/run_demos.py"], cwd=ROOT,
                       capture_output=True, check=True)
        after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout
        self.assertEqual(before, after, "跑完演示后不得出现新的已跟踪文件差异")


if __name__ == "__main__":
    unittest.main()
