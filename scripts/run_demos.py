"""Run the three generic demonstrations used by workspace acceptance tests."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPTS = (
    ROOT / "cases/examples/optimization/experiments/code/run_demo.py",
    ROOT / "cases/examples/data-analysis/experiments/code/run_demo.py",
    ROOT / "cases/examples/hybrid/experiments/code/run_demo.py",
)


def run_all() -> list[tuple[Path, int, str, str]]:
    results = []
    for script in DEMO_SCRIPTS:
        process = subprocess.run([sys.executable, str(script)], cwd=ROOT, text=True, capture_output=True, check=False)
        results.append((script, process.returncode, process.stdout, process.stderr))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="run generic modeling demonstrations")
    parser.parse_args()
    failed = False
    for script, code, stdout, stderr in run_all():
        print(f"=== {script.parent.parent.parent.name} ===")
        print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        if code:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
