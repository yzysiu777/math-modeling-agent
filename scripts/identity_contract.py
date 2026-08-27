"""Frozen project identity registry shared by human-only validators.

Identity is data owned by the case manifest, not a role string supplied by an
actor. The registry is intentionally small: one frozen human owner and an
explicit allow-list of independent reviewers.
"""

from __future__ import annotations

import json
from pathlib import Path


ALLOWED_REVIEWER_ROLES = {"independent_adversary", "independent_reviewer"}


def load_record(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def registered_identities(manifest: dict) -> dict[str, set[str]]:
    """Return ``role -> IDs`` from the frozen manifest registry."""

    identities: dict[str, set[str]] = {
        "human_owner": set(),
        "independent_adversary": set(),
        "independent_reviewer": set(),
    }
    owner = manifest.get("owner")
    owner_id = owner.get("owner_id") if isinstance(owner, dict) else None
    if not isinstance(owner_id, str) or not owner_id.strip():
        owner_id = None
    if owner_id:
        identities["human_owner"].add(owner_id)
    for entry in manifest.get("identity_allowlist") or []:
        if not isinstance(entry, dict):
            continue
        identity_id = entry.get("id")
        role = entry.get("role")
        if isinstance(identity_id, str) and identity_id.strip() and role in identities:
            identities[role].add(identity_id)
    return identities


def validate_manifest_registry(manifest: dict, errors: list[str]) -> None:
    if manifest.get("record_type") != "project_manifest":
        errors.append("identity registry must be a project_manifest")
        return
    owner = manifest.get("owner")
    if not isinstance(owner, dict) or not isinstance(owner.get("owner_id"), str) or not owner.get("owner_id", "").strip():
        errors.append("project manifest must freeze owner.owner_id")
    elif owner.get("role") != "human_owner":
        errors.append("project manifest owner.role must be human_owner")
    allowlist = manifest.get("identity_allowlist")
    if not isinstance(allowlist, list):
        errors.append("project manifest identity_allowlist must be a list")
        return
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(allowlist):
        if not isinstance(entry, dict):
            errors.append(f"identity_allowlist[{index}] must be an object")
            continue
        identity_id = entry.get("id")
        role = entry.get("role")
        if not isinstance(identity_id, str) or not identity_id.strip() or role not in ALLOWED_REVIEWER_ROLES | {"human_owner"}:
            errors.append(f"identity_allowlist[{index}] has an invalid id or role")
            continue
        key = (role, identity_id)
        if key in seen:
            errors.append(f"duplicate registered identity: {role}:{identity_id}")
        seen.add(key)


def identity_is_registered(manifest: dict, identity_id: object, role: object) -> bool:
    if not isinstance(identity_id, str) or not isinstance(role, str):
        return False
    return identity_id in registered_identities(manifest).get(role, set())


def validate_independent_reviewer(manifest: dict, reviewer_id: object, reviewer_role: object, errors: list[str]) -> None:
    if reviewer_role not in ALLOWED_REVIEWER_ROLES:
        errors.append("reviewer must use an independent reviewer role")
    elif not identity_is_registered(manifest, reviewer_id, reviewer_role):
        errors.append("reviewer identity is not registered in the frozen project manifest")


def validate_human_owner(manifest: dict, identity_id: object, errors: list[str]) -> None:
    if not identity_is_registered(manifest, identity_id, "human_owner"):
        errors.append("human_owner identity is not the frozen project owner")
