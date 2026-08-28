import json
import unittest

from scripts.run_demos import run_all


class DemoTests(unittest.TestCase):
    def test_three_generic_demos_run_to_a_checked_baseline(self):
        results = run_all()
        self.assertEqual(len(results), 3)
        for script, code, stdout, stderr in results:
            self.assertEqual(code, 0, f"{script}: {stderr}")
            self.assertIn('"passed": true', stdout)
            json.loads(stdout)


if __name__ == "__main__":
    unittest.main()
