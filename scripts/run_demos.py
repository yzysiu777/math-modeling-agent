"""Run the three generic demonstrations used by workspace acceptance tests."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.experiment_board import validate_experiment_board  # noqa: E402
from scripts.model_pool import validate_candidate_pool  # noqa: E402


DEMO_SCRIPTS = (
    ROOT / "cases/examples/optimization/experiments/code/python/run_demo.py",
    ROOT / "cases/examples/data-analysis/experiments/code/python/run_demo.py",
    ROOT / "cases/examples/hybrid/experiments/code/python/run_demo.py",
)
DEMO_CASES = (
    ("optimization", DEMO_SCRIPTS[0].parents[3] / "models/candidates.md", DEMO_SCRIPTS[0].parents[3] / "experiments/board.md", DEMO_SCRIPTS[0]),
    ("data-analysis", DEMO_SCRIPTS[1].parents[3] / "models/candidates.md", DEMO_SCRIPTS[1].parents[3] / "experiments/board.md", DEMO_SCRIPTS[1]),
    ("hybrid", DEMO_SCRIPTS[2].parents[3] / "models/candidates.md", DEMO_SCRIPTS[2].parents[3] / "experiments/board.md", DEMO_SCRIPTS[2]),
)


def validate_demo_case(candidates: Path, board: Path) -> list[str]:
    return [
        *validate_candidate_pool(candidates),
        *validate_experiment_board(board),
    ]


def run_all() -> list[tuple[Path, int, str, str]]:
    results = []
    for _, candidates, board, script in DEMO_CASES:
        static_errors = validate_demo_case(candidates, board)
        if static_errors:
            output = {"passed": False, "static_errors": static_errors}
            results.append((script, 1, json.dumps(output, ensure_ascii=False), ""))
            continue
        process = subprocess.run([sys.executable, str(script)], cwd=ROOT, text=True, capture_output=True, check=False)
        results.append((script, process.returncode, process.stdout, process.stderr))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="run generic modeling demonstrations")
    parser.parse_args()
    failed = False
    for script, code, stdout, stderr in run_all():
        print(f"=== {script.parents[3].name} ===")
        print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        if code:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
