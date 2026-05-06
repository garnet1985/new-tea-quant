"""工作台 latest：优先读快照表最新一行，否则 discovery + 首条落库。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.infra.project_context.path_manager import PathManager
from core.modules.data_manager import DataManager
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

from .strategy_settings_service import StrategySettingsService

logger = logging.getLogger(__name__)

_MAX_ROW_REPAIR_LOOPS = 5


def _snapshot_model():
    return DataManager().get_table("sys_strategy_workbench_snapshot")


def _load_latest_row(model, strategy_name: str) -> Optional[Dict[str, Any]]:
    if model is None:
        return None
    rows = model.list_by_strategy(str(strategy_name), limit=1)
    if not rows:
        return None
    return dict(rows[0] or {})


def _row_usable(row: Dict[str, Any]) -> bool:
    return isinstance(row.get("settings_snapshot"), dict)


def fetch_workbench_snapshot_by_snapshot_id(
    strategy_name: str, snapshot_id: int
) -> Optional[Dict[str, Any]]:
    """
    按 ``strategy_name`` + 快照主键（表中 ``version``）读取一行。

    不存在、``snapshot_id`` 非正、或 ``settings_snapshot`` 不可用 → ``None``（与 **V2-08** 404 对齐）。
    """
    name = str(strategy_name or "").strip()
    sid = int(snapshot_id)
    if not name or sid <= 0:
        return None

    model = _snapshot_model()
    if model is None:
        logger.error("Workbench snapshot table is not registered")
        return None

    row = model.load_by_strategy_snapshot_id(name, sid)
    if not row or not _row_usable(row):
        return None
    return row


def fetch_latest_workbench_snapshot(strategy_name: str) -> Optional[Dict[str, Any]]:
    """
    返回该策略快照表最新一行；若无则自 userspace ``settings.py`` discovery 后写入首条。

    无法加载策略时返回 ``None``（仅依赖快照表与 discovery，无 BFF / Flask）。
    """
    name = str(strategy_name or "").strip()
    if not name:
        return None

    model = _snapshot_model()
    if model is None:
        logger.error("Workbench snapshot table is not registered")
        return None

    for _ in range(_MAX_ROW_REPAIR_LOOPS):
        row = _load_latest_row(model, name)
        if not row:
            break
        if _row_usable(row):
            return row
        sid = int(row.get("snapshot_id") or row.get("version") or 0)
        if sid <= 0:
            logger.warning("Unusable snapshot row for %s (missing version)", name)
            break
        logger.warning("Removing unusable workbench snapshot row strategy=%s snapshot_id=%s", name, sid)
        model.delete_snapshot_row(name, sid)

    folder = PathManager.userspace() / "strategies" / name
    discovered = StrategyDiscoveryHelper.load_strategy(folder)
    if discovered is None:
        return None

    merged = dict(discovered.settings.to_dict())
    settings_api, err = StrategySettingsService.normalize_runtime_settings(
        strategy_name=name,
        api_settings=merged,
    )
    if err or not settings_api:
        logger.error("Workbench cold start normalize failed for %s: %s", name, err)
        return None

    model.create_snapshot(name, settings_api, {})
    row = _load_latest_row(model, name)
    if not row or not _row_usable(row):
        return None
    return row
