"""Create an explicit, hash-recorded Claude review bundle.

The caller must whitelist every file. This prevents hidden reasoning and
unintended private files from being copied into a manual review session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_bundle(case_dir: Path, output_dir: Path, mode: str, files: list[str], review_id: str) -> Path:
    case_dir = case_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    entries = []
    for raw in files:
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"file must be relative to case directory: {raw}")
        source = (case_dir / relative).resolve()
        if not source.is_file() or case_dir not in source.parents:
            raise FileNotFoundError(f"not a regular file inside case directory: {raw}")
        target = output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        entries.append({"path": str(relative), "sha256": sha256(source), "bytes": source.stat().st_size})

    manifest = {
        "record_type": "review_bundle_manifest",
        "review_id": review_id,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_root": str(case_dir),
        "files": entries,
        "hidden_reasoning_included": False,
        "human_instruction": "Claude may read only these files; write only the review artifact or approved patch.",
    }
    (output_dir / "bundle_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    readme = [
        f"# Review Bundle {review_id}",
        "",
        f"Mode: `{mode}`",
        "",
        "This bundle was created from an explicit file whitelist. It contains no Codex hidden reasoning.",
        "Claude must not modify the source case or infer missing fields. In review mode write only a review report; in approved revision mode output a patch limited to the approved files.",
        "",
        "## Files",
    ]
    readme.extend(f"- `{entry['path']}` — SHA-256 `{entry['sha256']}`" for entry in entries)
    (output_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["blind", "adversarial", "reproduction", "paper"], required=True)
    parser.add_argument("--review-id", required=True)
    parser.add_argument("--file", action="append", dest="files", required=True)
    args = parser.parse_args()
    create_bundle(args.case_dir, args.output, args.mode, args.files, args.review_id)
    print(f"created review bundle: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
