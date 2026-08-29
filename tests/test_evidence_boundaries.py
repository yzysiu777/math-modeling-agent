"""MMAG-006 第二轮：Reviewer 报告的五组可复现绕过的定向反例。

每个测试对应 Reviewer 交接文档中的一条 P1，命名以 `test_p1_<n>_` 开头，便于逐条复核。
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.case_paths import EVIDENCE_ROOTS, is_traversal, resolve_in_case
from scripts.check_case import check_case
from scripts.create_case import create_case
from scripts.make_review_packet import build_packet


CLAIM_HEADER = (
    "| Claim ID | 论文位置 | 主张原文 | 强度 | 来源 EXP-ID | 数据文件 | 图/表 ID | 复算报告 | 状态 |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)
BOARD_HEADER = (
    "# 实验赛马板\n\n"
    "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|\n"
)


class EvidenceBoundaryTests(unittest.TestCase):
    # ------------------------------------------------------------------ 夹具

    def case(self, directory, case_id="ev"):
        case = create_case(case_id, "optimization", Path(directory))
        path = case / "checkpoint.yaml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        payload["routing"].update({"confirmed": True, "confirmed_route": "optimization",
                                   "confirmed_by": "队长", "note": "已对照题面核实"})
        payload["reviews"]["C1"] = "not_needed"
        payload["review_notes"]["C1"] = "题意由简报直接给定，无会改变路线的歧义"
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        (case / "models/comparison.md").write_text(
            "# 比较\n\n当前 Champion：M-01\n当前 Challenger：M-02\n", encoding="utf-8")
        return case

    def board(self, case, rows=(("EXP-001", "done", "判定：PASS；可行"),)):
        body = "".join(
            f"| {exp} | M-01 | 是否可行 | toy | toy | 成本 | low | {status} | {summary} | yes | 下一步 |\n"
            for exp, status, summary in rows)
        (case / "experiments/board.md").write_text(BOARD_HEADER + body, encoding="utf-8")

    def review(self, case, node):
        (case / "reviews" / f"{node}.md").write_text(
            f"# {node}\n\nReview ID: r-{node}\nCase ID: {case.name}\n"
            "Reviewer provider: human_specialist\nReviewer model: 人工专家\n"
            "Review session: fresh\nSaw main conversation: false\n"
            f"Critical node: {node}\n\n结论：PASS_WITH_LIMITATIONS，口径一致\n"
            "What was checked: 目标与约束\nWhat was not checked: 大规模实例\n", encoding="utf-8")

    def evidence(self, case, exp_id="EXP-001", passed=True, checks=None, report_exp=None):
        outputs = case / "experiments/outputs"
        (outputs / "data").mkdir(parents=True, exist_ok=True)
        (outputs / f"data/{exp_id}_solution.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (outputs / "checks").mkdir(parents=True, exist_ok=True)
        payload = {
            "exp_id": report_exp or exp_id,
            "checks": checks if checks is not None else
            [{"name": "capacity", "kind": "constraint", "passed": passed, "detail": ""}],
        }
        (outputs / f"checks/{exp_id}.json").write_text(json.dumps(payload), encoding="utf-8")
        (outputs / "figures").mkdir(parents=True, exist_ok=True)
        (outputs / "figures/manifest.md").write_text(
            "# 图表清单\n\n| FIG-ID | 来源 EXP-ID | 生成脚本 | 数据文件 | 图题草稿 | 论文位置 | 状态 |\n"
            "|---|---|---|---|---|---|---|\n"
            f"| FIG-001 | {exp_id} | plot.py | data.csv | 图题 | 第 4 章 | final |\n",
            encoding="utf-8")

    def claim(self, case, data_file="outputs/data/EXP-001_solution.csv",
              report="outputs/checks/EXP-001.json", figure="FIG-001",
              exp_id="EXP-001", status="verified"):
        (case / "paper/claim_map.md").write_text(
            "# 溯源\n\n" + CLAIM_HEADER +
            f"| CLM-001 | 摘要 | 全部算例均可行 | 可行解 | {exp_id} | {data_file} | "
            f"{figure} | {report} | {status} |\n", encoding="utf-8")

    def spec(self, case, probe_result="PASS", probe_exp="EXP-001", waiver="",
             probe_spec_id="SPEC-A1-M01-probe", write_probe=True,
             probe_route="M-01", probe_status="probe"):
        specs = case / "specs"
        specs.mkdir(exist_ok=True)
        if write_probe:
            (specs / f"{probe_spec_id}.md").write_text(
                f"---\nspec_id: {probe_spec_id}\ncase_id: {case.name}\nroute_id: {probe_route}\n"
                f"subproblem: 问题1\nmethod_family: heuristic\nstatus: {probe_status}\n"
                "language: python\n---\n", encoding="utf-8")
        (specs / "SPEC-A1-M01.md").write_text(
            f"---\nspec_id: SPEC-A1-M01\ncase_id: {case.name}\nroute_id: M-01\nsubproblem: 问题1\n"
            f"method_family: heuristic\nstatus: full\nlanguage: python\n"
            f"probe_spec_id: {probe_spec_id}\nprobe_exp_id: {probe_exp}\n"
            f"probe_result: {probe_result}\nprobe_waiver_reason: {waiver}\n---\n", encoding="utf-8")

    def codes(self, report, code):
        return [f for f in report.findings if f.code == code]

    # ------------------------------------------------- P1-1 路径解析不得逃出案例

    def test_p1_1_parent_traversal_reference_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "secret.txt").write_text("TOP-SECRET", encoding="utf-8")
            case = self.case(root / "cases")
            (case / "sub").mkdir(exist_ok=True)
            self.assertTrue(is_traversal("sub/../../../secret.txt"))
            self.assertIsNone(resolve_in_case(case, "sub/../../../secret.txt"))
            self.assertIsNone(resolve_in_case(case, "sub/../../../secret.txt", kind="data"))

    def test_p1_1_absolute_reference_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "secret.txt").write_text("TOP-SECRET", encoding="utf-8")
            case = self.case(root / "cases")
            self.assertIsNone(resolve_in_case(case, str(root / "secret.txt")))

    def test_p1_1_symlink_out_of_the_case_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            case = self.case(root / "cases")
            data = case / "experiments/outputs/data"
            data.mkdir(parents=True, exist_ok=True)
            os.symlink(root / "outside.csv", data / "linked.csv")
            self.assertIsNone(resolve_in_case(case, "outputs/data/linked.csv", kind="data"))

    def test_p1_1_legitimate_result_file_still_resolves(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            resolved = resolve_in_case(case, "outputs/data/EXP-001_solution.csv", kind="data")
            self.assertIsNotNone(resolved)
            self.assertTrue(resolved.is_file())
            self.assertEqual(resolved.name, "EXP-001_solution.csv")

    def test_p1_1_evidence_kinds_are_isolated_from_each_other(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            # 数据文件不能借 checks 通道解析，反之亦然
            self.assertIsNone(resolve_in_case(case, "outputs/data/EXP-001_solution.csv", kind="checks"))
            self.assertIsNone(resolve_in_case(case, "outputs/checks/EXP-001.json", kind="data"))
            self.assertEqual(set(EVIDENCE_ROOTS) >= {"data", "checks", "figures"}, True)

    # ------------------------- P1-2 claim 不得引用非结果文件、不得留空复算报告

    def test_p1_2_non_result_file_cannot_back_a_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case)
            for node in ("C1", "C2", "C3"):
                self.review(case, node)
            self.claim(case, data_file="models/comparison.md")
            report = check_case(case, "final")
        hit = self.codes(report, "CLAIM_EVIDENCE_MISSING")
        self.assertTrue(hit)
        self.assertTrue(any("outputs/data" in f.reason for f in hit))
        self.assertEqual(report.exit_code, 1)

    def test_p1_2_empty_check_report_cannot_back_a_verified_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case)
            self.review(case, "C3")
            self.claim(case, report="", status="verified")
            report = check_case(case, "paper_claims")
        hit = self.codes(report, "CLAIM_EVIDENCE_MISSING")
        self.assertTrue(any("未填写复算报告" in f.reason for f in hit))
        self.assertTrue(all(f.blocks for f in hit))

    def test_p1_2_report_for_another_experiment_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case, report_exp="EXP-999")
            self.review(case, "C3")
            self.claim(case)
            report = check_case(case, "paper_claims")
        self.assertTrue(any("不一致" in f.reason for f in self.codes(report, "CLAIM_EVIDENCE_MISSING")))

    def test_p1_2_empty_checks_list_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case, checks=[])
            self.review(case, "C3")
            self.claim(case)
            report = check_case(case, "paper_claims")
        self.assertTrue(any("没有任何检查项" in f.reason
                            for f in self.codes(report, "CLAIM_EVIDENCE_MISSING")))

    def test_p1_2_string_false_is_not_a_passing_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case, checks=[{"name": "capacity", "kind": "constraint", "passed": "false"}])
            self.review(case, "C3")
            self.claim(case)
            report = check_case(case, "paper_claims")
        self.assertTrue(any("不是布尔值" in f.reason
                            for f in self.codes(report, "CLAIM_EVIDENCE_MISSING")))

    def test_p1_2_matching_data_and_report_still_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case)
            self.review(case, "C3")
            self.claim(case)
            report = check_case(case, "paper_claims")
        self.assertFalse([f for f in report.findings if f.code.startswith("CLAIM")])

    # ------------------------------- P1-3 缺失证据在 paper_claims 也必须阻断

    def test_p1_3_missing_evidence_blocks_at_both_stages(self):
        cases = {
            "缺 CSV": dict(data_file="outputs/data/missing.csv"),
            "缺报告": dict(report="outputs/checks/missing.json"),
            "未知图": dict(figure="FIG-404"),
        }
        for label, kwargs in cases.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.case(directory)
                    self.board(case)
                    self.evidence(case)
                    for node in ("C1", "C2", "C3"):
                        self.review(case, node)
                    self.claim(case, **kwargs)
                    claiming = check_case(case, "paper_claims")
                    final = check_case(case, "final")
                hit_claiming = self.codes(claiming, "CLAIM_EVIDENCE_MISSING")
                self.assertTrue(hit_claiming, label)
                self.assertTrue(all(f.blocks for f in hit_claiming), label)
                self.assertEqual(claiming.exit_code, 1, label)
                self.assertTrue(all(f.blocks for f in self.codes(final, "CLAIM_EVIDENCE_MISSING")), label)
                self.assertEqual(final.exit_code, 1, label)

    def test_p1_3_corrupt_report_blocks_at_both_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case)
            self.review(case, "C3")
            self.claim(case)
            (case / "experiments/outputs/checks/EXP-001.json").write_text("{broken", encoding="utf-8")
            claiming = check_case(case, "paper_claims")
        self.assertTrue(any("无法解析" in f.reason and f.blocks
                            for f in self.codes(claiming, "CLAIM_EVIDENCE_MISSING")))
        self.assertEqual(claiming.exit_code, 1)

    def test_p1_3_stale_figure_blocks_at_paper_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.evidence(case)
            self.review(case, "C3")
            self.claim(case)
            manifest = case / "experiments/outputs/figures/manifest.md"
            manifest.write_text(manifest.read_text(encoding="utf-8").replace("| final |", "| stale |"),
                                encoding="utf-8")
            claiming = check_case(case, "paper_claims")
        self.assertTrue(any(f.blocks for f in self.codes(claiming, "CLAIM_EVIDENCE_MISSING")))

    def test_p1_3_empty_claim_map_only_reminds_at_paper_claims(self):
        """论文骨架尚未建立是进度问题，不是证据问题。"""

        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.review(case, "C3")
            claiming = check_case(case, "paper_claims")
        skeleton = [f for f in claiming.findings if "claim_map" in f.reason]
        self.assertTrue(skeleton)
        self.assertFalse(any(f.blocks for f in skeleton))

    # --------------------------- P1-4 probe PASS 必须绑定真实成功实验

    def test_p1_4_empty_board_cannot_close_the_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case, rows=())
            self.spec(case)
            report = check_case(case, "model_selection")
        self.assertTrue(any("实验板为空" in f.reason for f in self.codes(report, "PROBE_NOT_CLOSED")))

    def test_p1_4_unfinished_or_failed_experiment_cannot_close_the_probe(self):
        for status in ("failed", "skipped", "queued", "running"):
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.case(directory)
                    self.board(case, rows=(("EXP-001", status, "判定：PASS"),))
                    self.spec(case)
                    report = check_case(case, "model_selection")
                self.assertTrue(self.codes(report, "PROBE_NOT_CLOSED"), status)

    def test_p1_4_done_without_an_explicit_pass_verdict_cannot_close(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case, rows=(("EXP-001", "done", "跑完了，看起来不错"),))
            self.spec(case)
            report = check_case(case, "model_selection")
        self.assertTrue(any("没有明确的 PASS 判定" in f.reason
                            for f in self.codes(report, "PROBE_NOT_CLOSED")))

    def test_p1_4_recorded_fail_verdict_cannot_close(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case, rows=(("EXP-001", "done", "判定：FAIL；间隙过大"),))
            self.spec(case)
            report = check_case(case, "model_selection")
        self.assertTrue(any("未通过判定" in f.reason for f in self.codes(report, "PROBE_NOT_CLOSED")))

    def test_p1_4_missing_probe_spec_cannot_close(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.spec(case, write_probe=False)
            report = check_case(case, "model_selection")
        self.assertTrue(any("找不到对应文件" in f.reason for f in self.codes(report, "PROBE_NOT_CLOSED")))

    def test_p1_4_probe_spec_that_is_not_a_probe_cannot_close(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.spec(case, probe_status="full")
            report = check_case(case, "model_selection")
        self.assertTrue(any("指向的不是 probe 规格" in f.reason
                            for f in self.codes(report, "PROBE_NOT_CLOSED")))

    def test_p1_4_route_mismatch_between_probe_and_full_cannot_close(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.spec(case, probe_route="M-09")
            report = check_case(case, "model_selection")
        self.assertTrue(any("路线不一致" in f.reason for f in self.codes(report, "PROBE_NOT_CLOSED")))

    def test_p1_4_valid_probe_and_experiment_close_the_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.spec(case)
            report = check_case(case, "model_selection")
        self.assertFalse(self.codes(report, "PROBE_NOT_CLOSED"))

    def test_p1_4_valid_waiver_still_closes_the_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case, rows=())
            self.spec(case, probe_result="WAIVED",
                      waiver="题面第 3 问直接指定该调度算法，无替代方法族可比")
            report = check_case(case, "model_selection")
        self.assertFalse(self.codes(report, "PROBE_NOT_CLOSED"))

    def test_p1_4_pending_blocks_before_paper_claims_only(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.board(case)
            self.spec(case, probe_result="PENDING")
            exploring = check_case(case, "exploration")
            selecting = check_case(case, "model_selection")
            self.evidence(case)
            self.review(case, "C3")
            self.claim(case)
            claiming = check_case(case, "paper_claims")
        self.assertFalse(self.codes(exploring, "PROBE_NOT_CLOSED"))
        self.assertTrue(self.codes(selecting, "PROBE_NOT_CLOSED"))
        self.assertFalse(self.codes(selecting, "PROBE_NOT_CLOSED")[0].blocks)
        self.assertTrue(all(f.blocks for f in self.codes(claiming, "PROBE_NOT_CLOSED")))

    # ------------------------------------ P1-5 packet_complete 不得误报

    def test_p1_5_c1_with_only_numeric_data_is_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            (case / "input/nodes.csv").write_text("id,x,y\n1,0,0\n", encoding="utf-8")
            packet = build_packet(case, "C1")
        self.assertIn("packet_complete: false", packet)
        self.assertIn("只有数据附件", packet)
        self.assertIn("数据附件", packet)

    def test_p1_5_c1_with_a_named_statement_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            (case / "input/nodes.csv").write_text("id,x,y\n1,0,0\n", encoding="utf-8")
            (case / "input/题面.md").write_text("# 原题\n\n某公司有两个服务点。\n", encoding="utf-8")
            packet = build_packet(case, "C1")
        self.assertIn("packet_complete: true", packet)
        self.assertIn("题面依据", packet)
        self.assertIn("某公司有两个服务点", packet)

    def test_p1_5_c1_statement_declared_in_input_readme_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            (case / "input/attachment_1.md").write_text("# 甲\n\n原始题目正文在此。\n", encoding="utf-8")
            (case / "input/README.md").write_text(
                "# 原始输入\n\n- `attachment_1.md`：本题题面\n", encoding="utf-8")
            packet = build_packet(case, "C1")
        self.assertIn("packet_complete: true", packet)
        self.assertIn("原始题目正文在此", packet)

    def test_p1_5_c3_unrelated_report_does_not_fill_the_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            checks = case / "experiments/outputs/checks"
            checks.mkdir(parents=True, exist_ok=True)
            (checks / "EXP-999.json").write_text(json.dumps(
                {"exp_id": "EXP-999", "checks": [{"name": "x", "kind": "constraint", "passed": True}]}),
                encoding="utf-8")
            self.claim(case, data_file="", report="", figure="")
            packet = build_packet(case, "C3")
        self.assertIn("packet_complete: false", packet)
        self.assertIn("没有填写数据文件", packet)
        self.assertIn("没有填写复算报告", packet)

    def test_p1_5_c3_report_for_another_experiment_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case, report_exp="EXP-999")
            self.claim(case)
            packet = build_packet(case, "C3")
        self.assertIn("packet_complete: false", packet)
        self.assertIn("不能替这条主张背书", packet)

    def test_p1_5_c3_with_matching_evidence_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            self.claim(case)
            packet = build_packet(case, "C3")
        self.assertIn("packet_complete: true", packet)
        self.assertIn("CLM-001 的结果数据片段", packet)
        self.assertIn("CLM-001 的复算报告", packet)
        self.assertIn("CLM-001 的图表清单条目", packet)

    def test_p1_5_c3_figure_is_optional_when_the_claim_leaves_it_blank(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.case(directory)
            self.evidence(case)
            self.claim(case, figure="—")
            packet = build_packet(case, "C3")
        self.assertIn("packet_complete: true", packet)


class PacketOverwriteTests(unittest.TestCase):
    """次要项 3：显式 --out 不得静默覆盖已存在的文件。"""

    def run_cli(self, case, out, extra=()):
        import subprocess, sys
        return subprocess.run(
            [sys.executable, "scripts/make_review_packet.py", "--case-dir", str(case),
             "--node", "C2", "--out", str(out), *extra],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False)

    def test_explicit_out_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("ov", "optimization", Path(directory))
            out = Path(directory) / "packet.md"
            first = self.run_cli(case, out)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = out.read_text(encoding="utf-8")

            second = self.run_cli(case, out)
            self.assertEqual(second.returncode, 1)
            self.assertIn("已存在", second.stdout)
            self.assertEqual(out.read_text(encoding="utf-8"), original)

            forced = self.run_cli(case, out, extra=("--force",))
            self.assertEqual(forced.returncode, 0, forced.stderr)


if __name__ == "__main__":
    unittest.main()
