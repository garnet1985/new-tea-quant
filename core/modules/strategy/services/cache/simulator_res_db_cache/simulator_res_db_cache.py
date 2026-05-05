#!/usr/bin/env python3
"""
``simulator_res_db_cache`` 包的 **对外编排入口**（本文件）。

三条 API 的 **编排步骤（pipeline）写在本文件各函数体内**；**settings → env → 双指纹** 见
``finger_print.finger_print.resolve_db_cache_fingerprints``（内部分层：``settings_resolver`` / ``env_resolver``）；
其余持久化等放在 ``orchestration/``、``apply/`` 等。

写 / 读缓存须 **显式传入 ``stock_ids``**、``latest_completed_trading_date``（与回测 flow 同源）；其余 env 因子仍由规范化 settings + worker/mapping 解析。
**不在用户持久化的 settings 上自动改写** ``sampling`` 空日期；仅在构建 env 指纹时使用副本 + fallback。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.tables.ui_bff.strategy_workbench_snapshot.model import SysStrategyWorkbenchSnapshotModel

from .config import (
    RESULT_KEY_CAPITAL_ALLOCATION,
    RESULT_KEY_PRICE_FACTOR,
    SIMULATOR_CAPITAL_ALLOCATION,
    SIMULATOR_ENUM,
    SIMULATOR_PRICE_FACTOR,
)
from .persistence.snapshot_persist import (
    replace_enum_cache_by_fingerprints,
    strip_result_summary_keys_by_fingerprints,
    try_load_cached_summary,
)
from .domain.snapshot_service import StrategyWorkbenchSnapshotService
from .orchestration.apply.file_write import atomic_write_text
from .orchestration.apply.paths import resolve_strategy_settings_path
from .orchestration.apply.serialize_settings import (
    backup_existing_settings_file,
    settings_dict_to_settings_py_source,
)
from .finger_print.finger_print import resolve_db_cache_fingerprints
from .service import DbCacheService
from .settings import StrategySettingsService

__all__ = ["apply_cache", "read_cache", "write_cache"]


def write_cache(
    *,
    simulator_name: str,
    strategy_name: str,
    raw_settings: Dict[str, Any],
    stock_ids: List[str],
    latest_completed_trading_date: str,
    result_summary_patch: Dict[str, Any],
    force_refresh: bool = False,
    workbench_run_id: Optional[str] = None,
) -> int:
    """
    **产生（写入）缓存**：在 ``strategy_name + settings_fp + env_fp`` 命中的行上
    更新 ``result_summary`` 中对应模拟器键；必要时新建行；返回 snapshot_id（失败或不写入则为 0）。

    **股票列表** 由 ``stock_ids`` 提供；**最新已完成交易日** 由 ``latest_completed_trading_date`` 提供（与 flow 一致，用于空 ``end_date`` fallback）；其余由步骤内解析：**run_mode**、**系统版本**、**worker**、**契约 mapping 文件指纹**（不含 ``settings['data']``，该块由 settings 指纹跟踪），再调 ``DbCacheService.generate_cache``。

    **校验失败**：返回 ``0``（与「未写入则无 snapshot_id」一致）；不在此抛 ``ValueError``，便于调用方按返回码分支。
    """
    # step 1–9 — 校验 settings + 解析 env/universe/worker/mapping → ``(settings_fp, env_fp)``
    resolved = resolve_db_cache_fingerprints(
        strategy_name=strategy_name,
        raw_settings=dict(raw_settings or {}),
        stock_ids=list(stock_ids or []),
        latest_completed_trading_date=str(latest_completed_trading_date or "").strip(),
    )
    if resolved is None:
        return 0

    settings_fp = resolved.settings_fp
    env_fp = resolved.env_fp
    stock_ids = resolved.stock_ids
    env_start_date = resolved.env_start_date
    env_end_date = resolved.env_end_date
    run_mode = resolved.run_mode
    engine_version = resolved.engine_version
    data_contract_mapping = resolved.data_contract_mapping

    # step 10 — 若 force_refresh：按 simulator 剥离对应 ``result_summary`` 顶层键（与 ``DbCacheService.generate_cache`` 一致）
    if force_refresh:
        sim = str(simulator_name or "").strip().lower()
        if sim == SIMULATOR_ENUM:
            replace_enum_cache_by_fingerprints(
                strategy_name=str(strategy_name),
                settings_finger_print_id=settings_fp,
                env_fingerprint_id=env_fp,
            )
        elif sim == SIMULATOR_PRICE_FACTOR:
            strip_result_summary_keys_by_fingerprints(
                strategy_name=str(strategy_name),
                settings_finger_print_id=settings_fp,
                env_fingerprint_id=env_fp,
                keys=(RESULT_KEY_PRICE_FACTOR,),
            )
        elif sim == SIMULATOR_CAPITAL_ALLOCATION:
            strip_result_summary_keys_by_fingerprints(
                strategy_name=str(strategy_name),
                settings_finger_print_id=settings_fp,
                env_fingerprint_id=env_fp,
                keys=(RESULT_KEY_CAPITAL_ALLOCATION,),
            )

    # step 11 — ``DbCacheService.generate_cache``（持久化 ``result_summary`` 分支）
    # step 12 — 写入成功后 ``prune_oldest_if_over_limit``（在 ``generate_cache`` 内）
    # step 13 — 返回 snapshot_id（失败或未写入为 ``0``）
    try:
        sid = DbCacheService().generate_cache(
            simulator_name,
            strategy_name,
            dict(raw_settings or {}),
            dict(result_summary_patch or {}),
            stock_ids=stock_ids,
            start_date=env_start_date,
            end_date=env_end_date,
            worker_module_path=resolved.worker_module_path,
            worker_class_name=resolved.worker_class_name,
            worker_code_hash=resolved.worker_code_hash,
            data_contract_mapping=data_contract_mapping,
            force_refresh=False,
            run_mode=run_mode,
            engine_version=engine_version,
            workbench_run_id=workbench_run_id,
        )
        return int(sid or 0)
    except Exception:
        return 0


def read_cache(
    *,
    strategy_name: str,
    raw_settings: Dict[str, Any],
    stock_ids: List[str],
    latest_completed_trading_date: str,
) -> Optional[Tuple[List[Dict[str, Any]], int]]:
    """
    **读取枚举缓存**：调用方提供 **策略名 + 当前 settings + 与写缓存相同的 ``stock_ids``、``latest_completed_trading_date``**；由编排层解析与 ``write_cache`` 相同的
    **settings_fp / env_fp**，再按双指纹 AND 命中且行仍「新鲜」时，返回枚举摘要行列表与 ``snapshot_id``。

    解析失败（settings 不可用或与写路径一致的 worker 异常）→ ``None``（与未命中相同返回形状时由调用方区分若需要）。

    当前持久化读路径仅 **枚举**；价格/资金若将来扩展，可在本函数增加分支或新 API。
    """
    # step 1–9 — 与 ``write_cache`` 同源：``finger_print.resolve_db_cache_fingerprints``
    resolved = resolve_db_cache_fingerprints(
        strategy_name=strategy_name,
        raw_settings=dict(raw_settings or {}),
        stock_ids=list(stock_ids or []),
        latest_completed_trading_date=str(latest_completed_trading_date or "").strip(),
    )
    if resolved is None:
        return None

    # step 10 — 委托 ``try_load_cached_summary``（查表 / 新鲜度 / enum 物化）
    return try_load_cached_summary(
        strategy_name,
        resolved.settings_fp,
        resolved.env_fp,
    )


def apply_cache(
    *,
    strategy_name: str,
    version_id: str,
) -> Dict[str, Any]:
    """
    **应用快照 settings 到 userspace**：按 ``v{n}`` 读表 ``settings_snapshot``，覆盖写入 ``userspace/strategies/<name>/settings.py``。

    不落 ``result_summary``；实现委托 ``StrategyWorkbenchSnapshotService``、``orchestration.apply``。

    **返回约定**（编排层 / CLI / BFF 可自行映射）：

    - 成功：``ok=True``，含 ``snapshot_id``、``snapshot_label``（与表 ``version`` 对应的 ``v{n}``）、``settings_file``。
    - 失败：``ok=False``，含 ``error``（``invalid_version_id`` | ``snapshot_row_not_found`` |
      ``invalid_snapshot_settings`` | ``settings_write_failed``），部分情况带 ``snapshot_id``。
    """
    # step 1 — 解析 ``version_id`` → ``snapshot_id``
    snapshot_id = StrategyWorkbenchSnapshotService.parse_version_id(version_id)
    if snapshot_id is None:
        return {"ok": False, "error": "invalid_version_id"}

    sid = int(snapshot_id)

    # step 2 — 按 strategy + snapshot_id 读表
    row = SysStrategyWorkbenchSnapshotModel().load_by_strategy_snapshot_id(
        strategy_name, sid
    )
    if not row:
        return {"ok": False, "error": "snapshot_row_not_found", "snapshot_id": sid}

    # step 3 — 取 ``settings_snapshot`` dict（表列已规范化为 dict）
    settings_snapshot = row.get("settings_snapshot")
    if not isinstance(settings_snapshot, dict):
        settings_snapshot = {}

    # step 4 — ``StrategySettings`` 校验后再写入磁盘形状（API → runtime → validate）
    normalized, _detail = StrategySettingsService.normalize_runtime_settings(
        strategy_name=strategy_name,
        api_settings=settings_snapshot,
    )
    if normalized is None:
        return {
            "ok": False,
            "error": "invalid_snapshot_settings",
            "snapshot_id": sid,
        }

    # step 5 — ``orchestration.apply.paths.resolve_strategy_settings_path``
    settings_path = resolve_strategy_settings_path(strategy_name)

    try:
        # step 6 — 备份既有 ``settings.py``；生成可读的格式化源码（内存已就绪，无需「先 repr 再美化」双写）
        backup_existing_settings_file(settings_path)
        source = settings_dict_to_settings_py_source(normalized, pretty=True)

        # step 7 — 原子写 ``settings.py``（策略发现侧下次 ``import_module`` 即见新内容）
        atomic_write_text(settings_path, source)
    except Exception:
        return {
            "ok": False,
            "error": "settings_write_failed",
            "snapshot_id": sid,
        }

    # step 8 — 成功（不落 ``result_summary``）
    return {
        "ok": True,
        "snapshot_id": sid,
        "snapshot_label": StrategyWorkbenchSnapshotService.format_snapshot_id(sid),
        "settings_file": str(settings_path),
    }
