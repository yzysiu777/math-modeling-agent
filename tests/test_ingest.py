from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.case_sources import SourceConfigError, load_sources
from scripts.create_case import create_case
from scripts.check_case import check_case
from scripts.ingest import (
    ExtractedText,
    _write_statement,
    excerpt_problem,
    ingest_case,
    statement_provenance_problem,
)
from scripts.make_review_packet import build_packet


def write_sources(
    case: Path,
    statement: Path,
    data_root: Path,
    *,
    questions: str = "  q1: 第一题",
    statement_value: str | None = None,
    data_value: str | None = None,
) -> None:
    (case / "sources.yaml").write_text(
        f"""statement: {statement_value or statement}
data_roots:
  - {data_value or data_root}
docs: []
questions:
{questions}
shared: []
""",
        encoding="utf-8",
    )


def write_minimal_xlsx(path: Path, headers: list[str]) -> None:
    cells = "".join(
        f'<c r="{chr(65 + index)}1" t="inlineStr"><is><t>{header}</t></is></c>'
        for index, header in enumerate(headers)
    )
    values = "".join(
        f'<c r="{chr(65 + index)}2"><v>{index}</v></c>'
        for index in range(len(headers))
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="SheetA" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData><row r="1">{cells}</row><row r="2">{values}</row></sheetData></worksheet>',
        )


class SourceConfigTests(unittest.TestCase):
    def test_missing_required_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case-a"
            case.mkdir()
            (case / "sources.yaml").write_text("statement: /tmp/x\n", encoding="utf-8")
            with self.assertRaisesRegex(SourceConfigError, "缺少字段"):
                load_sources(case)

    def test_relative_source_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            statement = root / "statement.md"
            statement.write_text("题面", encoding="utf-8")
            data = root / "data"
            data.mkdir()
            write_sources(case, statement, data, statement_value="../statement.md")
            with self.assertRaisesRegex(SourceConfigError, "相对路径只能指向案例目录内，案例外的来源必须写绝对路径"):
                load_sources(case)

    def test_relative_source_path_inside_case_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            statement = case / "input/source/statement.md"
            statement.parent.mkdir(parents=True)
            statement.write_text("题面", encoding="utf-8")
            data = case / "input/source/data"
            (data / "第一题").mkdir(parents=True)
            write_sources(
                case,
                statement,
                data,
                statement_value="input/source/statement.md",
                data_value="input/source/data",
            )
            sources = load_sources(case)
            self.assertEqual(sources.statement, statement.resolve())
            self.assertEqual(sources.data_roots, (data.resolve(),))

    def test_nonexistent_source_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            data = root / "data"
            data.mkdir()
            write_sources(case, root / "missing.pdf", data)
            with self.assertRaisesRegex(SourceConfigError, "路径不存在"):
                load_sources(case)

    def test_nonexistent_question_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            statement = root / "statement.md"
            statement.write_text("题面", encoding="utf-8")
            data = root / "data"
            data.mkdir()
            write_sources(case, statement, data, questions="  q1: 不存在的题目目录")
            with self.assertRaisesRegex(SourceConfigError, "questions.q1.*均不存在"):
                load_sources(case)

    def test_question_mapping_must_match_question_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            statement = root / "statement.md"
            statement.write_text("题面", encoding="utf-8")
            data = root / "data"
            data.mkdir()
            write_sources(case, statement, data, questions="  q1: 第一题\n  q2: 第二题")
            with self.assertRaisesRegex(SourceConfigError, "目录不一致"):
                load_sources(case)


class IngestTests(unittest.TestCase):
    def test_excerpt_detector_rejects_a_far_shorter_extract(self):
        self.assertIn("疑似摘录", excerpt_problem(1000, 100))
        self.assertEqual(excerpt_problem(1000, 900), "")
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case-a"
            (case / "input").mkdir(parents=True)
            source = Path(tmp) / "statement.md"
            source.write_text("完整文本", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "疑似摘录"):
                _write_statement(case, ExtractedText("短摘录", "test", 1000, 1000, (source,)))

    def test_ingest_writes_provenance_all_columns_docs_and_question_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            statement = root / "statement.md"
            statement.write_text("完整题面" * 100, encoding="utf-8")
            data = root / "data"
            question_data = data / "第一题"
            question_data.mkdir(parents=True)
            shared_data = data / "共享数据"
            shared_data.mkdir()
            columns = [f"field_{index}" for index in range(1, 9)]
            (question_data / "eight.csv").write_text(
                ",".join(columns) + "\n" + ",".join(str(index) for index in range(8)) + "\n",
                encoding="utf-8",
            )
            xlsx_columns = [f"sheet_field_{index}" for index in range(1, 9)]
            write_minimal_xlsx(question_data / "eight.xlsx", xlsx_columns)
            (data / "格式说明.txt").write_text(
                "产品数据包括采样高度、风向、风速、垂直速度、可信度与 Cn2。\n",
                encoding="utf-8",
            )
            write_sources(case, statement, data)
            source_text = (case / "sources.yaml").read_text(encoding="utf-8")
            (case / "sources.yaml").write_text(
                source_text.replace("shared: []", "shared:\n  - 共享数据"), encoding="utf-8"
            )

            ingest_case(case)

            statement_text = (case / "input/题面全文.md").read_text(encoding="utf-8")
            for marker in ("来源绝对路径", "源字节数", "抽取工具", "抽取后字符数"):
                self.assertIn(marker, statement_text)
            inventory = (case / "input/数据清单.md").read_text(encoding="utf-8")
            for column in columns:
                self.assertIn(column, inventory)
            for column in xlsx_columns:
                self.assertIn(column, inventory)
            self.assertIn("SheetA=2", inventory)
            self.assertIn("Cn2", inventory)
            self.assertTrue(any((case / "input/说明文档").glob("*.md")))
            scope = (case / "q1/数据范围.md").read_text(encoding="utf-8")
            self.assertIn(str(question_data.resolve()), scope)
            self.assertIn(str(shared_data.resolve()), scope)
            card = build_packet(case, "C1", "C1-test", "q1")
            self.assertIn(str(statement.resolve()), card)
            self.assertIn("q1/brief.md", card)
            self.assertNotIn("card_ready: false", card)

    def test_clean_ingest_scout_reports_no_anomaly_without_copying_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            statement = root / "statement.md"
            statement.write_text("完整题面" * 100, encoding="utf-8")
            data = root / "data"
            question_data = data / "第一题"
            question_data.mkdir(parents=True)
            columns = [f"very_long_field_{index}" for index in range(1, 9)]
            (question_data / "clean.csv").write_text(
                ",".join(columns) + "\n" + ",".join(str(index) for index in range(8)) + "\n",
                encoding="utf-8",
            )
            write_sources(case, statement, data)

            ingest_case(case)

            inventory = (case / "input/数据清单.md").read_text(encoding="utf-8")
            scout = (case / "队员工作区/数据踏勘速览.md").read_text(encoding="utf-8")
            self.assertIn(", ".join(columns), inventory)
            self.assertIn("未发现异常", scout)
            self.assertNotIn(", ".join(columns), scout)
            self.assertIn("文件数：1", scout)


class InventoryScaleTests(unittest.TestCase):
    """真实赛题里上千个雷达文件共用一套上千列的表头，逐文件重复会把清单撑爆。"""

    def _build(self, root: Path, wide_files: int) -> Path:
        case = create_case("scale-case", cases_root=root / "cases")
        source = root / "src"
        (source / "第一题" / "雷达").mkdir(parents=True)
        # 真实雷达 CSV 把距离库当列名，一份表头上千列、上千个文件共用它。
        wide = "azim," + ",".join(f"{index * 0.06:.2f}" for index in range(1, 400))
        body = "\n".join(
            f"{row}," + ",".join("9999.0" if row == 2 else "0.5" for _ in range(399))
            for row in range(1, 9)
        )
        for index in range(wide_files):
            (source / "第一题" / "雷达" / f"scan{index:03d}.csv").write_text(
                f"{wide}\n{body}\n", encoding="utf-8"
            )
        (source / "第一题" / "探空.csv").write_text(
            "时间,高度,水平风速,Cn2\n1,100,3.2,-14.2\n", encoding="utf-8"
        )
        (root / "statement.md").write_text("本题要求建立模型。" * 40, encoding="utf-8")
        write_sources(case, root / "statement.md", source)
        ingest_case(case)
        return case

    def test_shared_column_signature_is_printed_once_not_per_file(self):
        with tempfile.TemporaryDirectory() as name:
            case = self._build(Path(name), wide_files=40)
            inventory = (case / "input/数据清单.md").read_text(encoding="utf-8")
            # 宽表头只完整出现一次，而不是每个文件一次。
            self.assertEqual(inventory.count("23.94"), 1)
            # 40 个同结构文件合并成一行分组。
            self.assertIn("| 40 |", inventory)
            self.assertLess(len(inventory), 60_000)

    def test_every_distinct_column_set_still_appears_in_full(self):
        with tempfile.TemporaryDirectory() as name:
            case = self._build(Path(name), wide_files=40)
            inventory = (case / "input/数据清单.md").read_text(encoding="utf-8")
            # 分组不得让任何一列消失 —— 这正是上次实测漏掉 Cn2 的那类失败。
            for column in ("时间", "高度", "水平风速", "Cn2"):
                self.assertIn(column, inventory)

    def test_scout_aggregates_repeated_anomalies_into_one_line(self):
        with tempfile.TemporaryDirectory() as name:
            case = self._build(Path(name), wide_files=40)
            scout = (case / "队员工作区/数据踏勘速览.md").read_text(encoding="utf-8")
            repeated = [
                line for line in scout.splitlines()
                if line.startswith("- 缺测标记候选值")
            ]
            self.assertEqual(len(repeated), 1)
            self.assertIn("40 个文件", repeated[0])
            self.assertLess(len(scout.splitlines()), 40)

    def test_total_size_is_human_readable(self):
        with tempfile.TemporaryDirectory() as name:
            case = self._build(Path(name), wide_files=40)
            scout = (case / "队员工作区/数据踏勘速览.md").read_text(encoding="utf-8")
            total = next(line for line in scout.splitlines() if line.startswith("- 文件数"))
            self.assertRegex(total, r"总大小：[0-9.]+ (?:B|KB|MB|GB)")


class HeaderlessDetectionTests(unittest.TestCase):
    """定宽记录文件的首行是记录标识，不是表头；报成表头比报未知更糟。"""

    def _ingest(self, root: Path, first_line: str) -> Path:
        case = create_case("headerless", cases_root=root / "cases")
        source = root / "src"
        (source / "第一题").mkdir(parents=True)
        rows = "\n".join(
            "  100.0  180.0    3.2    0.1   95.0   90.0  -14.2" for _ in range(6)
        )
        (source / "第一题" / "ROBS.txt").write_text(f"{first_line}\n{rows}\n", encoding="utf-8")
        (root / "statement.md").write_text("本题要求建立模型。" * 40, encoding="utf-8")
        write_sources(case, root / "statement.md", source)
        ingest_case(case)
        return case

    def test_record_marker_line_is_not_reported_as_a_two_column_header(self):
        with tempfile.TemporaryDirectory() as name:
            case = self._ingest(Path(name), "WNDROBS 01.20")
            inventory = (case / "input/数据清单.md").read_text(encoding="utf-8")
            self.assertNotIn("[WNDROBS, 01.20]", inventory)
            self.assertIn("col_7", inventory)
            self.assertIn("record_marker=WNDROBS 01.20", inventory)

    def test_headerless_file_is_flagged_for_human_confirmation(self):
        with tempfile.TemporaryDirectory() as name:
            case = self._ingest(Path(name), "WNDROBS 01.20")
            scout = (case / "队员工作区/数据踏勘速览.md").read_text(encoding="utf-8")
            self.assertIn("疑似无表头", scout)

    def test_a_real_header_of_matching_width_is_kept(self):
        with tempfile.TemporaryDirectory() as name:
            case = self._ingest(
                Path(name), "高度 风向 风速 垂直速度 水平可信度 垂直可信度 Cn2"
            )
            inventory = (case / "input/数据清单.md").read_text(encoding="utf-8")
            self.assertIn("Cn2", inventory)
            self.assertNotIn("col_7", inventory)


class StatementProvenanceTests(unittest.TestCase):
    @staticmethod
    def _write(path: Path, body: str, *, source_chars: int, extracted_chars: int) -> None:
        path.write_text(
            "> 来源绝对路径：/tmp/statement.md\n"
            "> 源字节数：1000\n"
            "> 抽取工具：test\n"
            f"> 源文本层字符数：{source_chars}\n"
            f"> 抽取后字符数：{extracted_chars}\n\n"
            f"{body}\n",
            encoding="utf-8",
        )

    def test_missing_provenance_is_rejected_through_ingest_and_case_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            statement = root / "statement.md"
            statement.write_text("完整题面" * 100, encoding="utf-8")
            data = root / "data"
            (data / "第一题").mkdir(parents=True)
            write_sources(case, statement, data)
            ingest_case(case)
            (case / "input/题面全文.md").write_text("一句话\n", encoding="utf-8")

            finding = next(
                item for item in check_case(case, "exploration").findings
                if item.code == "STATEMENT_PROVENANCE_INVALID"
            )
            self.assertEqual(finding.level, "REMINDER")
            self.assertIn("不是阶段 0 生成", finding.reason)

    def test_complete_provenance_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "题面全文.md"
            body = "完整题面" * 100
            self._write(path, body, source_chars=len(body), extracted_chars=len(body))
            self.assertEqual(statement_provenance_problem(path), "")

    def test_body_length_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "题面全文.md"
            self._write(path, "正文", source_chars=2, extracted_chars=20)
            self.assertEqual(statement_provenance_problem(path), "题面在阶段 0 之后被改写")

    def test_matching_body_length_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "题面全文.md"
            body = "正文内容"
            self._write(path, body, source_chars=len(body), extracted_chars=len(body))
            self.assertEqual(statement_provenance_problem(path), "")

    def test_excerpt_ratio_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "题面全文.md"
            body = "短" * 100
            self._write(path, body, source_chars=1000, extracted_chars=len(body))
            self.assertIn("题面疑似摘录", statement_provenance_problem(path))

    def test_adequate_ratio_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "题面全文.md"
            body = "足" * 600
            self._write(path, body, source_chars=1000, extracted_chars=len(body))
            self.assertEqual(statement_provenance_problem(path), "")


if __name__ == "__main__":
    unittest.main()
