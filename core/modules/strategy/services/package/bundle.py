"""Strategy share bundle export, preview, and import."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from core.infra.export_import import (
    BundleManifest,
    ConflictPolicy,
    InstallResult,
    create_bundle_archive,
    extract_bundle_archive,
    install_bundle_archive,
    preflight_install,
)
from core.infra.project_context import ProjectContextManager

ctx = ProjectContextManager()  # module-level instance


from .resolver import resolve_strategy_bundle_specs

BytesOrPath = Union[bytes, Path]


def _read_core_version() -> str:
    system_json = ctx.get_project_root() / "core" / "system.json"
    if not system_json.is_file():
        return ""
    try:
        data = json.loads(system_json.read_text(encoding="utf-8"))
        version = str(data.get("version") or "").strip()
        return version if version.startswith("v") else (f"v{version}" if version else "")
    except Exception:
        return ""


def export_strategy_bundle(
    strategy_name: str,
    *,
    output_path: Path | None = None,
) -> Tuple[BundleManifest, BytesOrPath]:
    """Export a strategy share bundle (strategy + resolved on-disk dependencies)."""
    specs = resolve_strategy_bundle_specs(strategy_name)
    metadata = {
        "bundle_type": "strategy",
        "strategy_name": str(strategy_name).strip(),
        "core_version": _read_core_version(),
    }
    return create_bundle_archive(specs, metadata=metadata, output_path=output_path)


def preview_strategy_bundle_import(
    archive: Union[Path, bytes],
    *,
    userspace_root: Path | None = None,
    policy: ConflictPolicy = ConflictPolicy.SKIP_EXISTING,
) -> Dict[str, Any]:
    """Preview install outcome: per-entry status and conflicts."""
    us = Path(userspace_root) if userspace_root is not None else ctx.get_userspace_root()
    _, manifest = extract_bundle_archive(archive)
    plan = preflight_install(manifest, us, policy)

    skipped_keys = {e.target_relative for e in plan.skipped}
    install_keys = {e.target_relative for e in plan.to_install}
    conflict_keys = {c.target_relative for c in plan.conflicts}

    items: List[Dict[str, Any]] = []
    for entry in manifest.entries:
        target = entry.target_relative
        if target in conflict_keys:
            status = "conflict"
        elif target in skipped_keys:
            status = "exists_skip"
        elif target in install_keys:
            status = "will_install"
        else:
            status = "unknown"

        items.append(
            {
                "kind": entry.kind,
                "name": entry.name,
                "target_relative": entry.target_relative,
                "status": status,
            }
        )

    return {
        "ok": plan.ok,
        "policy": policy.value,
        "bundle_type": manifest.metadata.get("bundle_type"),
        "scope": manifest.metadata.get("scope"),
        "entity_name": manifest.metadata.get("entity_name"),
        "strategy_name": manifest.metadata.get("strategy_name"),
        "core_version": manifest.metadata.get("core_version"),
        "items": items,
        "conflicts": [
            {
                "kind": c.kind,
                "name": c.name,
                "target_relative": c.target_relative,
                "reason": c.reason,
            }
            for c in plan.conflicts
        ],
    }


def import_strategy_bundle(
    archive: Union[Path, bytes],
    policy: ConflictPolicy,
    *,
    userspace_root: Path | None = None,
) -> InstallResult:
    """Install a strategy share bundle into userspace."""
    us = Path(userspace_root) if userspace_root is not None else ctx.get_userspace_root()
    return install_bundle_archive(archive, us, policy)
