import re
import subprocess
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
    def test_case_creation_uses_per_question_workbenches_without_empty_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = create_case("demo-case", "hybrid", Path(tmp), questions=3)
            for question in ("q1", "q2", "q3"):
                self.assertTrue((case / question / "brief.md").is_file())
                self.assertTrue((case / question / "board.md").is_file())
                self.assertTrue((case / question / "log.md").is_file())
            self.assertFalse((case / "reviews/packets").exists())
            self.assertFalse((case / "reports").exists())
            self.assertTrue((case / "sources.yaml").is_file())
            files = [path for path in case.rglob("*") if path.is_file()]
            self.assertEqual(len(files), 18)
            self.assertFalse(any("待 Orchestrator 汇总" in path.read_text(encoding="utf-8") for path in files))
            workspace = case / "队员工作区"
            self.assertEqual(
                {path.name for path in workspace.iterdir() if path.is_file()},
                {"现在做什么.md", "审核卡索引.md", "我的笔记.md"},
            )
            self.assertEqual(
                {path.name for path in workspace.iterdir() if path.is_dir()},
                {"待批准", "已批准", "启动提示词"},
            )
            self.assertFalse(any(path.is_dir() for directory in workspace.iterdir() if directory.is_dir() for path in directory.iterdir()))
            workspace_text = "\n".join(
                path.read_text(encoding="utf-8") for path in workspace.glob("*.md")
            )
            for copied_marker in ("无评价发散（至少六条）", "要回答的问题/显式假设", "## 1. 目标与判据"):
                self.assertNotIn(copied_marker, workspace_text)
            codes = {finding.code for finding in check_case(case, "exploration").findings}
            self.assertIn("INPUT_MATERIAL_MISSING", codes)

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
                validate_experiment_board(case / "q1/board.md"), []
            )
            self.assertEqual(validate_case_specs(case), [])
            startup_codes = {finding.code for finding in check_case(case, "exploration").findings}
            self.assertNotIn("ROUTE_MISSING", startup_codes)
            self.assertNotIn("ROUTE_CONFIRMATION_REQUIRED", startup_codes)

    def test_examples_have_no_old_layout_markers(self):
        root = Path(__file__).resolve().parents[1] / "cases/examples"
        for route in ("optimization", "data-analysis", "hybrid"):
            case = root / route
            for retired in ("case_brief.md", "models", "experiments"):
                self.assertFalse((case / retired).exists(), f"{route}/{retired}")

    def test_committed_case_files_contain_no_user_or_home_absolute_paths(self):
        repo_root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            ["git", "ls-files", "-z", "cases"],
            cwd=repo_root,
            capture_output=True,
            check=True,
        )
        files = [
            repo_root / item.decode("utf-8")
            for item in proc.stdout.split(b"\0")
            if item
        ]
        home_pattern = re.compile(r"/(?:Users|home)/")
        offenders: list[str] = []
        for path in files:
            if not path.is_file() or path.suffix.casefold() in {".png", ".jpg", ".pdf", ".xlsx", ".parquet"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if home_pattern.search(line):
                    offenders.append(f"{path.relative_to(repo_root)}:{line_no}: {line.strip()}")
        self.assertEqual(offenders, [], "cases/ 下被提交的文件不应包含 /Users/ 或 /home/ 绝对路径")


if __name__ == "__main__":
    unittest.main()
