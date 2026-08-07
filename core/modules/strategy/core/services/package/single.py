"""Export a single userspace artifact (strategy / tag / adapter) without dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Union

from core.infra.export_import import ExportImport
from core.infra.project_context import ProjectContext

from .bundle import _read_core_version
from .paths import adapter_artifact_spec, strategy_artifact_spec, tag_artifact_spec

BytesOrPath = Union[bytes, Path]

_SINGLE_KINDS = frozenset({"strategy", "tag", "adapter"})


def resolve_single_entity_spec(kind: str, name: str) -> ExportImport.types.ArtifactSpec:
    """Resolve one on-disk artifact for single-entity export."""
    k = str(kind or "").strip().lower()
    n = str(name or "").strip()
    if k not in _SINGLE_KINDS:
        raise ValueError(f"unsupported single export kind: {kind!r} (use strategy, tag, or adapter)")
    if not n:
        raise ValueError("entity name is required for single export")

    if k == "strategy":
        source = ProjectContext.path.get_strategy_directory(n)
        if not source.is_dir():
            raise FileNotFoundError(f"strategy not found: {source}")
        return strategy_artifact_spec(n, source)

    if k == "tag":
        source = ProjectContext.path.get_tag_directory(n)
        if not source.is_dir():
            raise FileNotFoundError(f"tag scenario not found: {source}")
        return tag_artifact_spec(n, source)

    source = ProjectContext.path.get_adapters_directory() / n
    if not source.is_dir():
        raise FileNotFoundError(f"adapter not found: {source}")
    return adapter_artifact_spec(n, source)


def export_single_entity(
    kind: str,
    name: str,
    *,
    output_path: Path | None = None,
) -> Tuple[ExportImport.types.BundleManifest, BytesOrPath]:
    """Export one strategy, tag scenario, or adapter directory."""
    spec = resolve_single_entity_spec(kind, name)
    metadata = {
        "bundle_type": str(kind).strip().lower(),
        "entity_name": str(name).strip(),
        "scope": "single",
        "core_version": _read_core_version(),
    }
    return ExportImport.archive.create([spec], metadata=metadata, output_path=output_path)
