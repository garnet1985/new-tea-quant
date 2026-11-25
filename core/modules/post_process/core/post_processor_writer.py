"""写入 PostProcessor JSON（is_enabled / adapters + depends_on）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from core.modules.post_process.core.post_processor_loader import PostProcessorLoader
from core.modules.post_process.core.post_processor_types import (
    AdapterBinding,
    PostProcessorDefinition,
)
from core.modules.post_process.core.post_processor_validator import PostProcessorValidator
from core.modules.post_process.core.topo import topological_order


def _load_raw(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"PostProcessor JSON 须为对象: {path}")
    return dict(raw)


def _dump_raw(path: Path, raw: Dict[str, Any]) -> None:
    text = json.dumps(raw, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def set_enabled(key: str, enabled: bool) -> PostProcessorDefinition:
    """只改 ``is_enabled``；文件不存在则抛 ValueError。"""
    name = str(key or "").strip()
    if not name:
        raise ValueError("PostProcessor key 不能为空")
    path = PostProcessorLoader.resolve_path(name)
    if path is None:
        raise ValueError(f"PostProcessor 不存在: {name}")
    raw = _load_raw(path)
    raw["is_enabled"] = bool(enabled)
    if "key" not in raw:
        raw["key"] = name
    _dump_raw(path, raw)
    definition = PostProcessorLoader.load(name)
    if definition is None:
        raise ValueError(f"写入后无法加载 PostProcessor: {name}")
    return definition


def _normalize_adapters(
    adapters: Mapping[str, Any],
    *,
    previous: Optional[Dict[str, AdapterBinding]] = None,
) -> Dict[str, AdapterBinding]:
    prev = previous or {}
    out: Dict[str, AdapterBinding] = {}
    for adapter_name, body in dict(adapters or {}).items():
        aname = str(adapter_name or "").strip()
        if not aname:
            continue
        cfg: Dict[str, Any] = {}
        depends: List[str] = []
        if isinstance(body, dict):
            raw_cfg = body.get("config")
            if isinstance(raw_cfg, dict):
                cfg = dict(raw_cfg)
            elif aname in prev:
                cfg = dict(prev[aname].config or {})
            raw_deps = body.get("depends_on")
            if isinstance(raw_deps, str) and raw_deps.strip():
                depends = [raw_deps.strip()]
            elif isinstance(raw_deps, list):
                depends = [str(x).strip() for x in raw_deps if str(x).strip()]
        elif aname in prev:
            cfg = dict(prev[aname].config or {})
            depends = list(prev[aname].depends_on or [])
        out[aname] = AdapterBinding(name=aname, config=cfg, depends_on=depends)
    return out


def update_adapters(
    key: str,
    adapters: Mapping[str, Any],
) -> Tuple[PostProcessorDefinition, List[str]]:
    """写回 adapters（保留未提交的 config）；返回定义与拓扑序。"""
    name = str(key or "").strip()
    if not name:
        raise ValueError("PostProcessor key 不能为空")
    path = PostProcessorLoader.resolve_path(name)
    if path is None:
        raise ValueError(f"PostProcessor 不存在: {name}")
    current = PostProcessorLoader.load(name)
    if current is None:
        raise ValueError(f"无法加载 PostProcessor: {name}")

    bindings = _normalize_adapters(adapters, previous=current.adapters)
    trial = PostProcessorDefinition(
        key=current.key,
        name=current.name,
        is_enabled=current.is_enabled,
        on_error=current.on_error,
        on_empty=current.on_empty,
        adapters=bindings,
    )
    # 先做拓扑校验，避免写入坏 JSON
    order = topological_order(trial)

    raw = _load_raw(path)
    adapters_out: Dict[str, Any] = {}
    for aname, binding in bindings.items():
        body: Dict[str, Any] = {}
        if binding.config:
            body["config"] = dict(binding.config)
        if binding.depends_on:
            body["depends_on"] = list(binding.depends_on)
        adapters_out[aname] = body
    raw["adapters"] = adapters_out
    raw.pop("components", None)
    if "key" not in raw:
        raw["key"] = name
    _dump_raw(path, raw)

    ok, err = PostProcessorValidator.validate(name)
    if not ok:
        raise ValueError(err or f"PostProcessor 校验失败: {name}")
    definition = PostProcessorLoader.load(name)
    if definition is None:
        raise ValueError(f"写入后无法加载 PostProcessor: {name}")
    return definition, order


__all__ = ["set_enabled", "update_adapters"]
