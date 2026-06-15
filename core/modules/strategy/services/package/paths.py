"""Userspace-relative paths for strategy bundle artifacts."""

from __future__ import annotations

from pathlib import Path

from core.infra.export_import import ArtifactSpec

# Shipped with init userspace; omit from strategy share bundles by default.
BUILTIN_ADAPTERS_SKIP_EXPORT = frozenset({"console"})


def strategy_artifact_spec(strategy_name: str, source_dir: Path) -> ArtifactSpec:
    rel = f"strategies/{strategy_name}"
    return ArtifactSpec(
        kind="strategy",
        name=strategy_name,
        source_dir=Path(source_dir),
        archive_prefix=rel,
        target_relative=rel,
    )


def tag_artifact_spec(scenario_name: str, source_dir: Path) -> ArtifactSpec:
    rel = f"extensions/tags/{scenario_name}"
    return ArtifactSpec(
        kind="tag",
        name=scenario_name,
        source_dir=Path(source_dir),
        archive_prefix=rel,
        target_relative=rel,
    )


def adapter_artifact_spec(adapter_name: str, source_dir: Path) -> ArtifactSpec:
    rel = f"extensions/adapters/{adapter_name}"
    return ArtifactSpec(
        kind="adapter",
        name=adapter_name,
        source_dir=Path(source_dir),
        archive_prefix=rel,
        target_relative=rel,
    )
