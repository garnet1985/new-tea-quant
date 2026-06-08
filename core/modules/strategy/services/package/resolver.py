"""Resolve strategy bundle artifact specs from on-disk strategy settings."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

from core.infra.export_import import ArtifactSpec
from core.infra.project_context import PathManager
from core.modules.data_contract.contract_const import DataKey

from .paths import (
    BUILTIN_ADAPTERS_SKIP_EXPORT,
    adapter_artifact_spec,
    strategy_artifact_spec,
    tag_artifact_spec,
)
from .settings_loader import load_settings_dict_from_folder


def resolve_strategy_bundle_specs(strategy_name: str) -> List[ArtifactSpec]:
    """
    Collect exportable artifacts for a strategy share bundle.

    Always includes the strategy directory. Adds tag / adapter directories when
    referenced in settings and present on disk.
    """
    name = str(strategy_name or "").strip()
    if not name:
        raise ValueError("strategy_name is required")

    strategy_dir = PathManager.strategy(name)
    if not strategy_dir.is_dir():
        raise FileNotFoundError(f"strategy not found: {strategy_dir}")

    settings = load_settings_dict_from_folder(strategy_dir)
    specs: List[ArtifactSpec] = [strategy_artifact_spec(name, strategy_dir)]

    seen: Set[str] = {specs[0].normalized_archive_prefix()}

    for scenario in _tag_dependencies(settings):
        tag_dir = PathManager.tag_scenario(scenario)
        if not tag_dir.is_dir():
            continue
        spec = tag_artifact_spec(scenario, tag_dir)
        key = spec.normalized_archive_prefix()
        if key not in seen:
            specs.append(spec)
            seen.add(key)

    for adapter_name in _adapter_dependencies(settings):
        adapter_dir = PathManager.adapters() / adapter_name
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
    extras = data.get("extra_required_data_sources") if isinstance(data, dict) else []
    if not isinstance(extras, list):
        return []

    names: List[str] = []
    seen: Set[str] = set()
    for item in extras:
        if not isinstance(item, dict):
            continue
        data_id = str(item.get("data_id") or "").strip()
        if data_id not in (DataKey.TAG.value, "tag"):
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


def _adapter_dependencies(settings: Dict) -> List[str]:
    scanner = settings.get("scanner") if isinstance(settings.get("scanner"), dict) else {}
    adapters = scanner.get("adapters", ["console"]) if isinstance(scanner, dict) else ["console"]
    if isinstance(adapters, str):
        adapters = [adapters] if adapters else ["console"]
    if not isinstance(adapters, list):
        return []

    names: List[str] = []
    seen: Set[str] = set()
    for raw in adapters:
        adapter_name = str(raw or "").strip()
        if not adapter_name or adapter_name in BUILTIN_ADAPTERS_SKIP_EXPORT:
            continue
        if adapter_name not in seen:
            names.append(adapter_name)
            seen.add(adapter_name)
    return names
