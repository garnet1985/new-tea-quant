#!/usr/bin/env python3
"""
**指纹对外层**：对 ``settings_resolver`` / ``env_resolver`` 组装的 dict 做 **稳定 SHA256**，并暴露 DbCache 编排入口。

- **Resolver**：只负责收集、校验、组装结构化数据。
- **本模块**：``to_settings_hash`` / ``to_env_hash`` / ``settings_fingerprint_id`` / ``db_cache_fingerprint_pair*``。

部分函数体内延迟 import，避免包初始化循环依赖。
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple


def _stable_sha256(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def to_settings_hash(semantic_core_payload: Optional[Dict[str, Any]] = None) -> str:
    """语义核 dict → **settings 列**稳定哈希（内部 SHA256）。"""
    return _stable_sha256(
        {
            "v": 1,
            "kind": "strategy_workbench_settings_diff",
            "settings_diff": dict(semantic_core_payload or {}),
        }
    )


def to_env_hash(
    *,
    strategy_name: str,
    stock_ids: Sequence[str],
    run_mode: str,
    engine_version: str,
    worker_module_path: str = "",
    worker_class_name: str = "",
    worker_code_hash: str = "",
    data_contract_mapping: str = "",
    database_type: str = "",
) -> str:
    """env 因子 → **env 列**稳定哈希（内部先 ``env_fingerprint_payload`` 再 SHA256）。"""
    from .env_resolver import ResolveEnv, env_fingerprint_payload

    return _stable_sha256(
        env_fingerprint_payload(
            strategy_name=strategy_name,
            stock_ids=stock_ids,
            run_mode=run_mode,
            engine_version=engine_version,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_code_hash=worker_code_hash,
            data_contract_mapping=data_contract_mapping,
            database_type=database_type or ResolveEnv.resolve_storage_database_type(),
        )
    )


def settings_fingerprint_id(settings: Any) -> str:
    """``StrategySettings`` 实例 → 语义核 dict → settings 列指纹。"""
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings as _StrategySettings,
    )

    from .settings_resolver import semantic_core_from_strategy_settings

    if not isinstance(settings, _StrategySettings):
        raise TypeError("expected StrategySettings")
    return to_settings_hash(semantic_core_from_strategy_settings(settings))


class DbCacheFingerprintResolution(NamedTuple):
    """一次解析结果：差异字段、env 切片与 ``(settings_fp, env_fp)``。"""

    validated_settings: Any
    settings_diff: Dict[str, Any]  # 差异字段（只包含影响回测结果的字段）
    disk_settings_hash: str  # disk settings（物理文件）的 hash，用于检测物理文件是否被修改
    stock_ids: List[str]
    env_start_date: str
    env_end_date: str
    run_mode: str
    engine_version: str
    worker_module_path: str
    worker_class_name: str
    worker_code_hash: str
    data_contract_mapping: str
    settings_fp: str
    env_fp: str


def resolve_db_cache_fingerprints(
    *,
    strategy_name: str,
    disk_settings: Dict[str, Any],
    user_modified_settings: Dict[str, Any],
    stock_list: List[str],
    latest_completed_trading_date: str,
    data_manager: Optional[Any] = None,
    env_start_date: str = "",
    env_end_date: str = "",
) -> Optional[DbCacheFingerprintResolution]:
    """
    计算差异字段并生成指纹。

    Args:
        strategy_name: 策略名称
        disk_settings: 磁盘上的 settings（基准，从 userspace/strategies/{strategy_name}/settings.py 读取）
        user_modified_settings: 用户修改过的 settings（UI 上用户改动过后的 settings）
        stock_list: 股票列表
        latest_completed_trading_date: 最新完成的交易日
        data_manager: 数据管理器
        env_start_date: 环境开始日期
        env_end_date: 环境结束日期

    Returns:
        DbCacheFingerprintResolution 或 None

    流程：
    1. 计算 diff_and_filter(disk_settings, user_modified_settings) → 差异字段
    2. 差异字段 → 指纹
    3. 用户修改过的 settings → validated_normalized_snapshot → 验证后的 settings
    4. 验证后的 settings → resolve_env_inputs → env
    5. 返回 DbCacheFingerprintResolution
    """
    from .env_resolver import resolve_env_inputs
    from .settings_resolver import validated_normalized_snapshot
    from .settings_diff import diff_and_filter, filter_fingerprint_fields_from_settings

    # 计算差异字段
    diff_fields = diff_and_filter(disk_settings, user_modified_settings)

    # 计算 disk_settings_hash（基于影响回测结果的字段）
    disk_settings_filtered = filter_fingerprint_fields_from_settings(disk_settings)
    disk_settings_hash = to_settings_hash(disk_settings_filtered)

    # 验证用户修改过的settings（完整的settings）
    prepared = validated_normalized_snapshot(user_modified_settings)
    if prepared is None:
        return None
    validated_settings, normalized_settings_dict = prepared

    # 解析 env
    env = resolve_env_inputs(
        strategy_name=strategy_name,
        normalized_settings_dict=normalized_settings_dict,
        stock_list=stock_list,
        latest_completed_trading_date=latest_completed_trading_date,
        data_manager=data_manager,
        env_start_date=str(env_start_date or "").strip(),
        env_end_date=str(env_end_date or "").strip(),
    )
    if env is None:
        return None

    # 指纹基于差异字段
    settings_fp = to_settings_hash(diff_fields)
    env_fp = to_env_hash(
        strategy_name=strategy_name,
        stock_ids=env.stock_ids,
        run_mode=env.run_mode,
        engine_version=env.engine_version,
        worker_module_path=env.worker_module_path,
        worker_class_name=env.worker_class_name,
        worker_code_hash=env.worker_code_hash,
        data_contract_mapping=env.data_contract_mapping,
    )

    return DbCacheFingerprintResolution(
        validated_settings=validated_settings,
        settings_diff=diff_fields,  # 差异字段
        disk_settings_hash=disk_settings_hash,  # disk settings（物理文件）的 hash
        stock_ids=env.stock_ids,
        env_start_date=env.env_start_date,
        env_end_date=env.env_end_date,
        run_mode=env.run_mode,
        engine_version=env.engine_version,
        worker_module_path=env.worker_module_path,
        worker_class_name=env.worker_class_name,
        worker_code_hash=env.worker_code_hash,
        data_contract_mapping=env.data_contract_mapping,
        settings_fp=settings_fp,
        env_fp=env_fp,
    )


def _fingerprint_pair_from_env(
    *,
    validated_settings: Any,
    strategy_name: str,
    env: Any,
) -> tuple[str, str]:
    return db_cache_fingerprint_pair(
        settings=validated_settings,
        strategy_name=strategy_name,
        stock_ids=env.stock_ids,
        run_mode=env.run_mode,
        engine_version=env.engine_version,
        worker_module_path=env.worker_module_path,
        worker_class_name=env.worker_class_name,
        worker_code_hash=env.worker_code_hash,
        data_contract_mapping=env.data_contract_mapping,
    )


def db_cache_fingerprint_pair(
    *,
    settings: Any,
    strategy_name: str,
    stock_ids: Sequence[str],
    run_mode: Optional[str] = None,
    engine_version: Optional[str] = None,
    worker_module_path: str = "",
    worker_class_name: str = "",
    worker_code_hash: str = "",
    data_contract_mapping: str = "",
) -> Tuple[str, str]:
    """DB 列 ``(settings_finger_print_id, env_fingerprint_id)``（两列均为 hex 字符串）。"""
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings as _StrategySettings,
    )

    from ..config import derive_run_mode
    from .settings_resolver import _require_valid_snapshot, strip_to_semantic_core

    if not isinstance(settings, _StrategySettings):
        raise TypeError("expected StrategySettings")
    snap = _require_valid_snapshot(settings)
    core = strip_to_semantic_core(snap)
    rm = run_mode if run_mode is not None else derive_run_mode(snap)
    return (
        to_settings_hash(core),
        to_env_hash(
            strategy_name=strategy_name,
            stock_ids=stock_ids,
            run_mode=str(rm),
            engine_version=str(engine_version),
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_code_hash=worker_code_hash,
            data_contract_mapping=data_contract_mapping,
        ),
    )


def db_cache_fingerprint_pair_from_parts(
    *,
    semantic_core_payload: Dict[str, Any],
    strategy_name: str,
    stock_ids: Sequence[str],
    run_mode: str,
    engine_version: Optional[str] = None,
    worker_module_path: str = "",
    worker_class_name: str = "",
    worker_code_hash: str = "",
    data_contract_mapping: str = "",
) -> Tuple[str, str]:
    """在仅有语义核 dict 时产出指纹对（须显式传入 ``run_mode``；引擎版本默认读 module_info）。"""
    from ..config import read_strategy_module_version

    core = dict(semantic_core_payload or {})
    ev = engine_version if engine_version is not None else read_strategy_module_version()
    return (
        to_settings_hash(core),
        to_env_hash(
            strategy_name=strategy_name,
            stock_ids=stock_ids,
            run_mode=str(run_mode),
            engine_version=str(ev),
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_code_hash=worker_code_hash,
            data_contract_mapping=data_contract_mapping,
        ),
    )

__all__ = [
    "DbCacheFingerprintResolution",
    "db_cache_fingerprint_pair",
    "db_cache_fingerprint_pair_from_parts",
    "resolve_db_cache_fingerprints",
    "settings_fingerprint_id",
    "to_env_hash",
    "to_settings_hash",
]
