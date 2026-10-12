"""滚动对照按钮：三层回测齐全，并且 rolling.py 能读出窗口。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from core.modules.strategy.core.engines.rolling.config import (
    ROLLING_FILE_NAME,
    load_rolling_windows,
)
from core.modules.strategy.core.engines.rolling.pipeline import (
    fingerprints_for_settings,
    missing_backtest_steps,
)
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery import DiscoveryService

logger = logging.getLogger(__name__)

_TOOLTIP_NEED_RUN = "请先完成枚举、价格和资金回测。"
_TOOLTIP_NEED_CONFIG = "需要在策略目录配置 rolling.py 才能滚动测试。"
_TOOLTIP_INVALID = "rolling.py 存在但窗口无法使用。"


def describe_rolling_button(
    *,
    steps_ready: bool,
    config_state: str,
    has_report: bool,
    parent_version_id: str,
    window_count: int,
) -> Dict[str, Any]:
    """把三层完成情况和配置收成按钮状态。"""
    config_ok = config_state == "ok"
    enabled = bool(steps_ready and config_ok)
    if enabled:
        reason = "ok"
    elif not steps_ready and not config_ok:
        reason = "not_ready"
    elif not steps_ready:
        reason = "steps_incomplete"
    elif config_state == "invalid":
        reason = "rolling_invalid"
    else:
        reason = "rolling_not_configured"
    parts = []
    if not steps_ready:
        parts.append(_TOOLTIP_NEED_RUN)
    if config_state == "missing":
        parts.append(_TOOLTIP_NEED_CONFIG)
    elif config_state == "invalid":
        parts.append(_TOOLTIP_INVALID)
    return {
        "enabled": enabled,
        "reason": reason,
        "tooltip": "".join(parts),
        "has_report": bool(has_report and parent_version_id),
        "parent_version_id": str(parent_version_id or "").strip(),
        "window_count": int(window_count or 0),
        "steps_ready": bool(steps_ready),
        "config_ok": config_ok,
    }


def probe(key_or_id: str) -> Dict[str, Any]:
    """按当前 settings 判断这一版能不能滚动测试。"""
    strategy_info, folder = _open_strategy(key_or_id)
    config_state, window_count = _config_state(folder, strategy_info.key)
    parent, steps_ready = _finished_primary(strategy_info, folder)
    has_report = bool(parent) and _report_path(folder, parent).is_file()
    return describe_rolling_button(
        steps_ready=steps_ready,
        config_state=config_state,
        has_report=has_report,
        parent_version_id=parent,
        window_count=window_count,
    )


def report_path_for(key_or_id: str) -> Path:
    """当前主 version 的滚动报告路径。没有完成的主 version 时拒绝。"""
    strategy_info, folder = _open_strategy(key_or_id)
    parent, steps_ready = _finished_primary(strategy_info, folder)
    if not parent or not steps_ready:
        raise FileNotFoundError("当前 settings 还没有完成的三层回测，没有滚动报告。")
    path = _report_path(folder, parent)
    if not path.is_file():
        raise FileNotFoundError(f"还没有滚动报告: {path}")
    return path


def _open_strategy(key_or_id: str) -> Tuple[Any, Path]:
    """找到已启用策略及其目录。"""
    name = str(key_or_id or "").strip()
    strategy_info = DiscoveryService.find_strategy(name)
    if strategy_info is None:
        raise ValueError(f"当前策略不存在或未启用: {name}")
    return strategy_info, DiscoveryService.resolve_strategy_folder(name)


def _config_state(folder: Path, strategy_key: str) -> Tuple[str, int]:
    path = Path(folder) / ROLLING_FILE_NAME
    if not path.is_file():
        return "missing", 0
    try:
        windows = load_rolling_windows(folder, strategy_key=strategy_key)
    except (OSError, ValueError):
        return "invalid", 0
    return "ok", len(windows)


def _finished_primary(strategy_info: Any, folder: Path) -> Tuple[str, bool]:
    try:
        fp_res = fingerprints_for_settings(strategy_info, None)
        root = ArtifactStore.simulations_root(folder)
        parent = str(
            VersionMetaStore.find_version_by_fingerprints(
                root,
                str(fp_res.execute_fp or ""),
                str(fp_res.env_fp or ""),
            )
            or ""
        ).strip()
        if not parent:
            return "", False
        return parent, not missing_backtest_steps(root, parent)
    except (OSError, ValueError, TypeError, LookupError):
        logger.exception("rolling readiness probe failed strategy=%s", strategy_info.key)
        return "", False


def _report_path(folder: Path, parent: str) -> Path:
    root = ArtifactStore.simulations_root(folder)
    return root / str(parent).strip() / "rolling" / "report.json"


__all__ = ["describe_rolling_button", "probe", "report_path_for"]
