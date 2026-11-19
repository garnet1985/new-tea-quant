"""后处理启用开关：薄封装 PostProcess.set_enabled / set_run_enabled。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.post_process import PostProcess


def set_post_processor_enabled(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    key = args.get("key")
    enabled = args.get("is_enabled")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    if not isinstance(enabled, bool):
        return {"ok": False, "error": "is_enabled 须为布尔"}
    extra = set(args) - {"key", "is_enabled"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    try:
        PostProcess.set_enabled(key.strip(), enabled)
    except Exception as exc:
        return {"ok": False, "key": key.strip(), "error": str(exc)}
    return {
        "ok": True,
        "key": key.strip(),
        "is_enabled": enabled,
        "note": (
            "已写入 post_processor.yaml。"
            if enabled
            else "已关闭该方案；扫描后不会再跑它。"
        ),
    }


def set_post_process_run_enabled(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    enabled = args.get("enabled")
    if not isinstance(enabled, bool):
        return {"ok": False, "error": "enabled 须为布尔"}
    extra = set(args) - {"enabled"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    try:
        value = PostProcess.set_run_enabled(enabled)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "enabled": bool(value),
        "note": (
            "工作区已允许扫描后处理。"
            if value
            else "工作区已关闭扫描后处理（所有方案都不会跑）。"
        ),
    }


def get_post_process_run_enabled(
    arguments: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    _ = arguments
    try:
        enabled = PostProcess.is_run_enabled()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "enabled": bool(enabled)}
