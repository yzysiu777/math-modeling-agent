import tempfile
import unittest
from pathlib import Path

from scripts.make_review_packet import _data_roots, _explanation_docs, build_packet


class ReviewCardBoundaryTests(unittest.TestCase):
    def _case(self, root: Path, prose: bool = False) -> tuple[Path, Path]:
        case = root / "case-a"
        data_root = root / "随题数据" / "第一题"
        (case / "input").mkdir(parents=True)
        data_root.mkdir(parents=True)
        (case / "case_brief.md").write_text("# brief\n", encoding="utf-8")
        (case / "input/原题全文.md").write_text("完整题面", encoding="utf-8")
        line = f"数据根（只读）：`{data_root}/`" if prose else f"data_root: {data_root}"
        (case / "input/README.md").write_text(line, encoding="utf-8")
        (data_root / "Nodes.csv").write_text("id\n1\n", encoding="utf-8")
        (data_root.parent / "风廓线雷达通用数据格式.doc").write_bytes(b"doc")
        (data_root.parent / "微波辐射计数据格式说明文档.docx").write_bytes(b"docx")
        return case, data_root

    def test_explicit_data_root_finds_parent_explanation_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            case, _ = self._case(Path(tmp))
            names = {path.name for path in _explanation_docs(_data_roots(case))}
            self.assertEqual(names, {"风廓线雷达通用数据格式.doc", "微波辐射计数据格式说明文档.docx"})

    def test_historical_prose_data_root_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            case, data = self._case(Path(tmp), prose=True)
            self.assertEqual(_data_roots(case), [data.resolve()])

    def test_card_references_originals_without_inlining_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            case, _ = self._case(Path(tmp))
            card = build_packet(case, "C1", "C1-test")
            self.assertIn("reviewer_provider: anthropic", card)
            self.assertIn("实际使用的 Claude 型号", card)
            self.assertIn("原题全文.md", card)
            self.assertIn("风廓线雷达通用数据格式.doc", card)
            self.assertNotIn("完整题面\n完整题面", card)
            self.assertLessEqual(len(card.encode("utf-8")), 6144)

    def test_symlink_outside_input_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case, _ = self._case(root)
            outside = root / "outside"
            outside.mkdir()
            (outside / "原题-secret.md").write_text("secret", encoding="utf-8")
            (case / "input/link").symlink_to(outside, target_is_directory=True)
            card = build_packet(case, "C1", "C1-test")
            self.assertNotIn("原题-secret.md", card)


if __name__ == "__main__":
    unittest.main()
