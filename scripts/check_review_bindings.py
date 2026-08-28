"""Bind every required critical review node to one concrete review artifact."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath

try:
    from .check_review_independence import validate_input_bindings, validate_review_record
    from .git_contract import validate_revision_pair, resolve_commit
    from .identity_contract import validate_independent_reviewer, validate_manifest_registry
    from .check_evidence_graph import load_record
except ImportError:  # pragma: no cover
    from check_review_independence import validate_input_bindings, validate_review_record
    from git_contract import validate_revision_pair, resolve_commit
    from identity_contract import validate_independent_reviewer, validate_manifest_registry
    from check_evidence_graph import load_record


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
CRITICAL_NODES = {"C1", "C2", "C3"}
MINIMUM_REVIEW_LENSES = {
    "C1": {"semantic_constraint_audit", "invariant_counterexample"},
    "C2": {"alternative_formulation", "implementation_consistency", "invariant_counterexample"},
    "C3": {"evidence_claim_audit", "implementation_consistency", "invariant_counterexample"},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        return None
    return str(path)


def validate_review_input_bindings(
    review: dict,
    workspace: Path,
    *,
    label: str,
) -> list[str]:
    """Validate structured review inputs against files in the active workspace."""

    errors: list[str] = []
    if "input_hashes" in review:
        errors.append(f"{label} uses legacy input_hashes; structured input_bindings are required")
    bindings = review.get("input_bindings")
    validate_input_bindings(bindings, errors, label=f"{label}.input_bindings")
    if not isinstance(bindings, list):
        return errors
    root = workspace.resolve()
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            continue
        item_label = f"{label}.input_bindings[{index}]"
        relative = safe_relative(binding.get("path"))
        expected = binding.get("sha256")
        if relative is None or not isinstance(expected, str) or not HEX64.fullmatch(expected):
            continue
        path = (workspace / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            errors.append(f"{item_label}.path escapes workspace")
            continue
        if not path.is_file():
            errors.append(f"{item_label}.path does not exist: {relative}")
            continue
        actual = sha256_file(path)
        if actual.lower() != expected.lower():
            errors.append(f"{item_label}.sha256 does not match: {relative}")
    return errors


def validate_review_bindings(
    bindings: object,
    required_nodes: list[str] | tuple[str, ...],
    *,
    case_id: str,
    revision_id: str,
    workspace: Path,
    manifest: dict | None = None,
    target_git_revision: str | None = None,
) -> list[str]:
    """Return errors for a one-to-one node -> review-record join."""

    errors: list[str] = []
    required = list(required_nodes)
    if len(required) != len(set(required)):
        errors.append("required review nodes contain duplicates")
    if required and manifest is None:
        errors.append("required review nodes need the frozen project identity registry")
    if not isinstance(bindings, list):
        return ["review_bindings must be a list"]
    if workspace is None:
        return [*errors, "workspace is required to read and hash review records"]
    if required and not target_git_revision:
        errors.append("required review nodes need the result Git revision")
    if target_git_revision:
        resolved_target = resolve_commit(workspace, target_git_revision)
        if resolved_target is None:
            errors.append(f"result Git revision is not a real full commit: {target_git_revision}")
        else:
            _, _ = validate_revision_pair(
                workspace,
                resolved_target,
                resolved_target,
                errors,
                require_result_at_head=False,
                label="review target Git revision",
            )
    if len(bindings) != len(set(required)):
        errors.append("review_bindings count must equal the number of required review nodes")
    seen_nodes: set[str] = set()
    seen_reviews: set[str] = set()
    seen_cases: set[tuple[str, str, str]] = set()
    for index, binding in enumerate(bindings):
        label = f"review_bindings[{index}]"
        if not isinstance(binding, dict):
            errors.append(f"{label} must be an object")
            continue
        required_fields = {"node", "review_id", "path", "sha256", "case_id", "target_revision", "target_git_revision", "input_bindings", "reviewer_id", "reviewer_role"}
        missing = required_fields.difference(binding)
        if missing:
            errors.append(f"{label} missing fields: {sorted(missing)}")
            continue
        node = binding.get("node")
        review_id = binding.get("review_id")
        binding_case = binding.get("case_id")
        target_revision = binding.get("target_revision")
        if node not in CRITICAL_NODES or node not in required:
            errors.append(f"{label} node is not required by this revision: {node}")
        if node in seen_nodes:
            errors.append(f"review node is bound more than once: {node}")
        seen_nodes.add(str(node))
        if not isinstance(review_id, str) or not review_id.strip() or review_id in seen_reviews:
            errors.append(f"{label} review_id is empty or reused")
        seen_reviews.add(str(review_id))
        if binding_case != case_id:
            errors.append(f"{label} case_id does not match the active case")
        if target_revision != revision_id:
            errors.append(f"{label} target_revision does not match the active revision")
        binding_target_git = binding.get("target_git_revision")
        if target_git_revision and binding_target_git != target_git_revision:
            errors.append(f"{label} target_git_revision does not match the result Git revision")
        identity_key = (str(review_id), str(binding_case), str(target_revision))
        if identity_key in seen_cases:
            errors.append(f"review record is reused for multiple bindings: {identity_key}")
        seen_cases.add(identity_key)
        relative = safe_relative(binding.get("path"))
        expected_hash = binding.get("sha256")
        if relative is None:
            errors.append(f"{label} path must be safe and relative")
            continue
        if not isinstance(expected_hash, str) or not HEX64.fullmatch(expected_hash):
            errors.append(f"{label} sha256 is invalid")
            continue
        path = (workspace / relative).resolve()
        try:
            path.relative_to(workspace.resolve())
        except ValueError:
            errors.append(f"{label} path escapes workspace")
            continue
        if not path.is_file():
            errors.append(f"{label} review file does not exist: {relative}")
            continue
        if sha256_file(path).lower() != expected_hash.lower():
            errors.append(f"{label} review file hash mismatch: {relative}")
        try:
            review = load_record(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{label} review file cannot be parsed: {exc}")
            continue
        if review.get("review_id") != review_id:
            errors.append(f"{label} review_id does not match the file")
        if review.get("case_id") != case_id:
            errors.append(f"{label} review record case_id does not match the active case")
        if review.get("target_revision") != revision_id:
            errors.append(f"{label} review record target_revision does not match the active revision")
        if review.get("target_git_revision") != binding_target_git:
            errors.append(f"{label} target_git_revision does not match the review record")
        if binding.get("input_bindings") != review.get("input_bindings"):
            errors.append(f"{label} input_bindings do not match the review record")
        errors.extend(validate_review_input_bindings(review, workspace, label=label))
        if binding.get("reviewer_id") != review.get("reviewer_id") or binding.get("reviewer_role") != review.get("reviewer_role"):
            errors.append(f"{label} reviewer identity does not match the review record")
        if review.get("critical_node") != node:
            errors.append(f"{label} review critical_node does not match the binding node")
        ok, review_errors = validate_review_record(review)
        if not ok:
            errors.extend(f"{label}: invalid review record: {error}" for error in review_errors)
        minimum = MINIMUM_REVIEW_LENSES.get(str(node), set())
        actual_lenses = set(review.get("review_lens") or [])
        if not minimum.issubset(actual_lenses):
            errors.append(f"{label} is missing node-specific minimum review lens: {sorted(minimum - actual_lenses)}")
        if manifest is not None:
            validate_manifest_registry(manifest, errors)
            validate_independent_reviewer(manifest, review.get("reviewer_id"), review.get("reviewer_role"), errors)
    if set(seen_nodes) != set(required):
        errors.append(f"review_bindings must cover each required node exactly once: required={required} actual={sorted(seen_nodes)}")
    if not required and bindings:
        errors.append("review_bindings must be empty when no review node is required")
    return sorted(set(errors))
