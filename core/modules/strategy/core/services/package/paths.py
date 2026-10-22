"""Userspace-relative paths for strategy bundle artifacts."""

from __future__ import annotations

from pathlib import Path

from core.infra.export_import import ExportImport

# Shipped with init userspace; omit from strategy share bundles by default.
BUILTIN_ADAPTERS_SKIP_EXPORT = frozenset({"console"})
BUILTIN_POST_PROCESSORS_SKIP_EXPORT = frozenset({"console"})


def strategy_artifact_spec(strategy_name: str, source_dir: Path) -> ExportImport.types.ArtifactSpec:
    rel = f"strategies/{strategy_name}"
    return ExportImport.types.ArtifactSpec(
        kind="strategy",
        name=strategy_name,
        source_dir=Path(source_dir),
        archive_prefix=rel,
        target_relative=rel,
    )


def tag_artifact_spec(scenario_name: str, source_dir: Path) -> ExportImport.types.ArtifactSpec:
    rel = f"extensions/tags/{scenario_name}"
    return ExportImport.types.ArtifactSpec(
        kind="tag",
        name=scenario_name,
        source_dir=Path(source_dir),
        archive_prefix=rel,
        target_relative=rel,
    )


def adapter_artifact_spec(component_name: str, source_dir: Path) -> ExportImport.types.ArtifactSpec:
    rel = f"extensions/post_process/adapters/{component_name}"
    return ExportImport.types.ArtifactSpec(
        kind="adapter",
        name=component_name,
        source_dir=Path(source_dir),
        archive_prefix=rel,
        target_relative=rel,
    )


def post_processor_artifact_spec(key: str, source_dir: Path) -> ExportImport.types.ArtifactSpec:
    rel = f"extensions/post_process/post_processors/{key}"
    return ExportImport.types.ArtifactSpec(
        kind="post_processor",
        name=key,
        source_dir=Path(source_dir),
        archive_prefix=rel,
        target_relative=rel,
    )
