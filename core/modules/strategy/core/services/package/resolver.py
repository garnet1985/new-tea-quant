"""Resolve strategy bundle artifact specs from on-disk strategy settings."""

from __future__ import annotations

from typing import Dict, List, Set

from core.infra.export_import import ExportImport
from core.infra.project_context import ProjectContext
from core.modules.data_contract.contracts import SYS_DATA_KEY

from .paths import (
    BUILTIN_ADAPTERS_SKIP_EXPORT,
    BUILTIN_POST_PROCESSORS_SKIP_EXPORT,
    adapter_artifact_spec,
    post_processor_artifact_spec,
    strategy_artifact_spec,
    tag_artifact_spec,
)
from .settings_loader import load_settings_dict_from_folder


def resolve_strategy_bundle_specs(strategy_name: str) -> List[ExportImport.types.ArtifactSpec]:
    """
    Collect exportable artifacts for a strategy share bundle.

    Always includes the strategy directory. Adds tag / post_processor / adapter
    directories when referenced in settings and present on disk.
    """
    name = str(strategy_name or "").strip()
    if not name:
        raise ValueError("strategy_name is required")

    strategy_dir = ProjectContext.path.get_strategy_directory(name)
    if not strategy_dir.is_dir():
        raise FileNotFoundError(f"strategy not found: {strategy_dir}")

    settings = load_settings_dict_from_folder(strategy_dir)
    specs: List[ExportImport.types.ArtifactSpec] = [strategy_artifact_spec(name, strategy_dir)]

    seen: Set[str] = {specs[0].normalized_archive_prefix()}

    for scenario in _tag_dependencies(settings):
        tag_dir = ProjectContext.path.get_tag_directory(scenario)
        if not tag_dir.is_dir():
            continue
        spec = tag_artifact_spec(scenario, tag_dir)
        key = spec.normalized_archive_prefix()
        if key not in seen:
            specs.append(spec)
            seen.add(key)

    pp_key = _post_process_key(settings)
    if pp_key and pp_key not in BUILTIN_POST_PROCESSORS_SKIP_EXPORT:
        from core.modules.post_process.core.post_processor_loader import PostProcessorLoader

        resolved = PostProcessorLoader.resolve_path(pp_key)
        if resolved is not None:
            source_dir = resolved.parent if resolved.is_file() else resolved
            if source_dir.name != "post_processors":
                spec = post_processor_artifact_spec(pp_key, source_dir)
                key = spec.normalized_archive_prefix()
                if key not in seen:
                    specs.append(spec)
                    seen.add(key)

        definition = PostProcessorLoader.load(pp_key)
        if definition is not None:
            for adapter_name in definition.adapters:
                if adapter_name in BUILTIN_ADAPTERS_SKIP_EXPORT:
                    continue
                adapter_dir = ProjectContext.path.get_adapters_directory() / adapter_name
                if not adapter_dir.is_dir():
                    continue
                spec = adapter_artifact_spec(adapter_name, adapter_dir)
                key = spec.normalized_archive_prefix()
                if key not in seen:
                    specs.append(spec)
                    seen.add(key)

    return specs


def _tag_dependencies(settings: Dict) -> List[str]:
    data = settings.get("data") if isinstance(settings.get("data"), dict) else {}
    required = data.get("required") if isinstance(data, dict) else []
    if not isinstance(required, list):
        return []

    names: List[str] = []
    seen: Set[str] = set()
    tag_key = str(SYS_DATA_KEY.TAG.value if hasattr(SYS_DATA_KEY.TAG, "value") else SYS_DATA_KEY.TAG)
    for item in required:
        if not isinstance(item, dict):
            continue
        data_key = str(item.get("data_key") or "").strip()
        if data_key not in (tag_key, "tag"):
            continue
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        scenario = ""
        for key in ("tag_scenario", "scenario_name"):
            raw = str(params.get(key) or "").strip()
            if raw:
                scenario = raw
                break
        if scenario and scenario not in seen:
            names.append(scenario)
            seen.add(scenario)
    return names


def _post_process_key(settings: Dict) -> str:
    scanner = settings.get("scanner") if isinstance(settings.get("scanner"), dict) else {}
    raw = scanner.get("post_process", "console") if isinstance(scanner, dict) else "console"
    return str(raw or "").strip() or "console"


__all__ = ["resolve_strategy_bundle_specs"]
