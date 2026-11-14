"""Adapter / PostProcessor 目录摘要（供 UI / BFF，不含 secrets）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.post_process.core.adapter_loader import AdapterLoader
from core.modules.post_process.core.adapter_readiness import check_adapter_readiness
from core.modules.post_process.core.adapter_validator import AdapterValidator
from core.modules.post_process.core.post_processor_loader import PostProcessorLoader
from core.modules.post_process.core.post_processor_validator import PostProcessorValidator
from core.modules.post_process.core.topo import topological_order


def summarize_adapter(name: str) -> Optional[Dict[str, Any]]:
    """返回单个 adapter 的目录摘要；不存在则 None。"""
    key = str(name or "").strip()
    if not key:
        return None
    if key not in AdapterLoader.list_names():
        return None
    ok, message = AdapterValidator.validate(key)
    defaults = AdapterLoader.load_default_config(key)
    display_name = str(
        defaults.get("display_name") or defaults.get("display_title") or ""
    ).strip()
    supports_dry_run = "dry_run" in defaults
    default_dry_run: Optional[bool] = None
    if supports_dry_run:
        default_dry_run = bool(defaults.get("dry_run"))
    readiness = check_adapter_readiness(key)
    return {
        "name": key,
        "display_name": display_name or key,
        "validate": {"ok": bool(ok), "message": str(message or "")},
        "supports_dry_run": supports_dry_run,
        "default_dry_run": default_dry_run,
        "readiness": {
            "ok": bool(readiness.get("ok")),
            "message": str(readiness.get("message") or ""),
            "missing": list(readiness.get("missing") or []),
        },
        "status": str(readiness.get("status") or "unavailable"),
        "remark": str(readiness.get("remark") or ""),
    }


def list_adapter_summaries() -> List[Dict[str, Any]]:
    """全部 adapter 目录摘要（稳定序）。"""
    out: List[Dict[str, Any]] = []
    for name in AdapterLoader.list_names():
        row = summarize_adapter(name)
        if row is not None:
            out.append(row)
    return out


def summarize_post_processor(key: str) -> Optional[Dict[str, Any]]:
    """返回单个 PostProcessor 摘要（含拓扑序与步骤 status）。"""
    name = str(key or "").strip()
    if not name:
        return None
    definition = PostProcessorLoader.load(name)
    if definition is None:
        return None
    ok, message = PostProcessorValidator.validate(name)
    adapters: List[Dict[str, Any]] = []
    for adapter_name, binding in sorted(definition.adapters.items()):
        defaults = AdapterLoader.load_default_config(adapter_name)
        merged = dict(defaults)
        merged.update(dict(binding.config or {}))
        display_name = str(
            defaults.get("display_name") or defaults.get("display_title") or ""
        ).strip()
        readiness = check_adapter_readiness(
            adapter_name, config_override=dict(binding.config or {})
        )
        supports_dry_run = "dry_run" in merged
        dry_run: Optional[bool] = bool(merged["dry_run"]) if supports_dry_run else None
        entry: Dict[str, Any] = {
            "name": adapter_name,
            "display_name": display_name or adapter_name,
            "depends_on": list(binding.depends_on or []),
            "validate": {
                "ok": bool(readiness.get("loadable")),
                "message": str(
                    ""
                    if readiness.get("loadable")
                    else readiness.get("message") or ""
                ),
            },
            "readiness": {
                "ok": bool(readiness.get("ok")),
                "message": str(readiness.get("message") or ""),
                "missing": list(readiness.get("missing") or []),
            },
            "supports_dry_run": supports_dry_run,
            "status": str(readiness.get("status") or "unavailable"),
            "remark": str(readiness.get("remark") or ""),
        }
        if dry_run is not None:
            entry["dry_run"] = dry_run
        adapters.append(entry)

    execution_order: List[str] = []
    order_error = ""
    try:
        execution_order = topological_order(definition)
    except ValueError as exc:
        order_error = str(exc)

    return {
        "key": definition.key,
        "name": definition.name or definition.key,
        "is_enabled": bool(definition.is_enabled),
        "on_error": definition.on_error,
        "on_empty": definition.on_empty,
        "adapters": adapters,
        "execution_order": execution_order,
        "order_error": order_error,
        "validate": {"ok": bool(ok), "message": str(message or "")},
    }


def list_post_processor_summaries() -> List[Dict[str, Any]]:
    """全部 PostProcessor 摘要（稳定序）。"""
    out: List[Dict[str, Any]] = []
    for key in PostProcessorLoader.list_keys():
        row = summarize_post_processor(key)
        if row is not None:
            out.append(row)
    return out


__all__ = [
    "list_adapter_summaries",
    "list_post_processor_summaries",
    "summarize_adapter",
    "summarize_post_processor",
]
