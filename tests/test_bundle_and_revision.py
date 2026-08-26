import json
import tempfile
import unittest
from pathlib import Path

from scripts.create_review_bundle import create_bundle


class ReviewBundleTests(unittest.TestCase):
    def test_bundle_is_explicit_and_hashed(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "case"
            output = Path(temp) / "bundle"
            case.mkdir()
            (case / "problem.md").write_text("problem", encoding="utf-8")
            (case / "hidden_reasoning.md").write_text("do not include", encoding="utf-8")
            create_bundle(case, output, "blind", ["problem.md"], "REV-TEST-001")
            manifest = json.loads((output / "bundle_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "blind")
            self.assertFalse(manifest["hidden_reasoning_included"])
            self.assertEqual([item["path"] for item in manifest["files"]], ["problem.md"])
            self.assertFalse((output / "hidden_reasoning.md").exists())


if __name__ == "__main__":
    unittest.main()
