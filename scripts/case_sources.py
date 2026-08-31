"""Parse the single source-of-truth path declaration for a competition case."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


QUESTION = re.compile(r"^q[1-9][0-9]*$", re.IGNORECASE)
REQUIRED_FIELDS = ("statement", "data_roots", "docs", "questions", "shared")


class SourceConfigError(ValueError):
    """Raised when ``sources.yaml`` cannot safely drive ingestion."""


@dataclass(frozen=True)
class CaseSources:
    statement: Path
    data_roots: tuple[Path, ...]
    docs: tuple[Path, ...]
    questions: dict[str, str]
    shared: tuple[str, ...]


def _relative_scope(value: Any, label: str, errors: list[str]) -> str:
    text = str(value or "").strip().strip("/\\")
    path = Path(text)
    if not text or path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} 必须是 data_roots 下的相对路径")
    return text


def _absolute_path(value: Any, label: str, errors: list[str]) -> Path:
    path = Path(str(value or "").strip()).expanduser()
    if not path.is_absolute():
        errors.append(f"{label} 必须是绝对路径：{value!r}")
    return path


def load_sources(
    case_dir: Path,
    *,
    require_existing_paths: bool = True,
    require_question_dirs: bool = True,
) -> CaseSources:
    path = case_dir / "sources.yaml"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise SourceConfigError(f"sources.yaml 无法读取：{exc}") from exc
    if not isinstance(payload, Mapping):
        raise SourceConfigError("sources.yaml 顶层必须是映射")

    errors = [f"缺少字段：{field}" for field in REQUIRED_FIELDS if field not in payload]
    statement = _absolute_path(payload.get("statement"), "statement", errors)

    raw_roots = payload.get("data_roots")
    if not isinstance(raw_roots, list) or not raw_roots:
        errors.append("data_roots 必须是非空列表")
        raw_roots = []
    data_roots = tuple(
        _absolute_path(value, f"data_roots[{index}]", errors)
        for index, value in enumerate(raw_roots)
    )

    raw_docs = payload.get("docs")
    if not isinstance(raw_docs, list):
        errors.append("docs 必须是列表")
        raw_docs = []
    docs = tuple(
        _absolute_path(value, f"docs[{index}]", errors)
        for index, value in enumerate(raw_docs)
    )

    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, Mapping) or not raw_questions:
        errors.append("questions 必须是非空映射")
        raw_questions = {}
    questions: dict[str, str] = {}
    for raw_key, value in raw_questions.items():
        key = str(raw_key).strip().casefold()
        if not QUESTION.fullmatch(key):
            errors.append(f"非法子问题键：{raw_key!r}")
            continue
        questions[key] = _relative_scope(value, f"questions.{key}", errors)
    expected = [f"q{index}" for index in range(1, len(questions) + 1)]
    if sorted(questions, key=lambda item: int(item[1:])) != expected:
        errors.append("questions 必须从 q1 开始连续编号")

    raw_shared = payload.get("shared")
    if not isinstance(raw_shared, list):
        errors.append("shared 必须是列表")
        raw_shared = []
    shared = tuple(
        _relative_scope(value, f"shared[{index}]", errors)
        for index, value in enumerate(raw_shared)
    )

    if require_existing_paths:
        path_specs = [(statement, "statement", None), *(
            (root, f"data_roots[{index}]", "dir") for index, root in enumerate(data_roots)
        ), *(
            (doc, f"docs[{index}]", None) for index, doc in enumerate(docs)
        )]
        for candidate, label, kind in path_specs:
            if not candidate.exists():
                errors.append(f"{label} 路径不存在：{candidate}")
            elif kind == "dir" and not candidate.is_dir():
                errors.append(f"{label} 必须是目录：{candidate}")
            elif not os.access(candidate, os.R_OK):
                errors.append(f"{label} 不可读：{candidate}")
        relative_paths = [
            *((f"questions.{key}", value) for key, value in questions.items()),
            *((f"shared[{index}]", value) for index, value in enumerate(shared)),
        ]
        for label, relative in relative_paths:
            candidates = [root / relative for root in data_roots]
            existing = [candidate for candidate in candidates if candidate.exists()]
            if not existing:
                errors.append(f"{label} 在任何 data_roots 下均不存在：{relative}")
            elif not any(os.access(candidate, os.R_OK) for candidate in existing):
                errors.append(f"{label} 不可读：{relative}")

    if require_question_dirs and questions:
        actual = {
            child.name.casefold()
            for child in case_dir.iterdir()
            if child.is_dir() and QUESTION.fullmatch(child.name)
        } if case_dir.is_dir() else set()
        expected_dirs = set(questions)
        if actual != expected_dirs:
            errors.append(
                "questions 与 q<k>/ 目录不一致："
                f"声明={sorted(expected_dirs)}，目录={sorted(actual)}"
            )

    if errors:
        raise SourceConfigError("；".join(errors))
    return CaseSources(statement, data_roots, docs, questions, shared)
