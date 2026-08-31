from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.case_sources import SourceConfigError, load_sources
from scripts.create_case import create_case
from scripts.ingest import ExtractedText, _write_statement, excerpt_problem, ingest_case
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
            write_sources(case, statement, data, statement_value="relative.md")
            with self.assertRaisesRegex(SourceConfigError, "绝对路径"):
                load_sources(case)

    def test_nonexistent_source_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = create_case("case-a", cases_root=root)
            data = root / "data"
            data.mkdir()
            write_sources(case, root / "missing.pdf", data)
            with self.assertRaisesRegex(SourceConfigError, "路径不存在"):
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


if __name__ == "__main__":
    unittest.main()
