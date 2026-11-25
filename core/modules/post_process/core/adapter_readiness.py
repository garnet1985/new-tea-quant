"""Adapter 就绪检查与 status 推导。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from core.infra.project_context import ProjectContext
from core.modules.post_process.core.adapter_loader import AdapterLoader
from core.modules.post_process.core.adapter_validator import AdapterValidator

STATUS_LIVE = "live"
STATUS_DRY_RUN = "dry_run"
STATUS_UNAVAILABLE = "unavailable"


def adapter_directory(name: str) -> Optional[Path]:
    key = str(name or "").strip()
    if not key:
        return None
    root = ProjectContext.path.get_adapters_directory() / key
    return root if root.is_dir() else None


def merge_adapter_config(
    name: str,
    *,
    config_override: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    merged = dict(AdapterLoader.load_default_config(name))
    if config_override:
        merged.update(dict(config_override))
    return merged


def derive_status(
    *,
    loadable: bool,
    dry_run: Optional[bool],
    live_ready: bool,
) -> str:
    """优先级：不可用 > 测试模式 > 可用。

    真发必备配置未齐 → unavailable（即使 dry_run=true）。
    配置齐且 dry_run → dry_run；配置齐且非 dry_run → live。
    """
    if not loadable or not live_ready:
        return STATUS_UNAVAILABLE
    if dry_run is True:
        return STATUS_DRY_RUN
    return STATUS_LIVE


def remark_for_status(status: str, *, message: str = "") -> str:
    """UI remark 文案。"""
    if status == STATUS_LIVE:
        return "可以正常使用"
    if status == STATUS_DRY_RUN:
        return "当前是测试模式"
    text = str(message or "").strip()
    if not text:
        return "缺少必要配置"
    if text.startswith("缺少"):
        return text
    return f"缺少配置：{text}"


def _parse_missing(message: str) -> List[str]:
    text = str(message or "").strip()
    if text.startswith("缺少："):
        return [
            part.strip()
            for part in text.replace("缺少：", "", 1).split("、")
            if part.strip()
        ]
    return []


def check_adapter_readiness(
    name: str,
    *,
    config_override: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """合并 settings 后检查真发必备配置，并给出 UI status / remark。"""
    key = str(name or "").strip()
    out: Dict[str, Any] = {
        "name": key,
        "ok": False,
        "message": "",
        "missing": [],
        "dry_run": None,
        "status": STATUS_UNAVAILABLE,
        "remark": "缺少必要配置",
        "loadable": False,
    }
    if not key:
        out["message"] = "adapter 名称不能为空"
        out["remark"] = remark_for_status(STATUS_UNAVAILABLE, message=out["message"])
        return out

    load_ok, load_msg = AdapterValidator.validate(key)
    out["loadable"] = bool(load_ok)
    if not load_ok:
        out["message"] = str(load_msg or "无法加载")
        out["status"] = STATUS_UNAVAILABLE
        out["remark"] = remark_for_status(STATUS_UNAVAILABLE, message=out["message"])
        return out

    cls = AdapterLoader.load_class(key)
    if cls is None:
        out["message"] = "无法加载 adapter 类"
        out["remark"] = remark_for_status(STATUS_UNAVAILABLE, message=out["message"])
        return out

    config = merge_adapter_config(key, config_override=config_override)
    if "dry_run" not in config:
        dry_run: Optional[bool] = None
    else:
        dry_run = bool(config.get("dry_run"))
    out["dry_run"] = dry_run

    directory = adapter_directory(key)
    # 着色一律按「真发必备」检查（忽略 dry_run 宽放行）
    live_config = dict(config)
    live_config["dry_run"] = False
    try:
        instance = cls(adapter_name=key)
        live_ok, live_msg = instance.check_readiness(
            live_config, adapter_directory=directory
        )
    except Exception as exc:
        out["ok"] = False
        out["message"] = f"check_readiness 失败: {exc}"
        out["status"] = STATUS_UNAVAILABLE
        out["remark"] = remark_for_status(STATUS_UNAVAILABLE, message=out["message"])
        return out

    out["ok"] = bool(live_ok)
    out["message"] = str(live_msg or "")
    out["missing"] = _parse_missing(out["message"])
    out["status"] = derive_status(
        loadable=True, dry_run=dry_run, live_ready=bool(live_ok)
    )
    out["remark"] = remark_for_status(out["status"], message=out["message"])
    return out


__all__ = [
    "STATUS_DRY_RUN",
    "STATUS_LIVE",
    "STATUS_UNAVAILABLE",
    "adapter_directory",
    "check_adapter_readiness",
    "derive_status",
    "merge_adapter_config",
    "remark_for_status",
]
