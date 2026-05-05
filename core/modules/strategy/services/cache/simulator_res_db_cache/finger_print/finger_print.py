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


def to_settings_hash(semantic_core_payload: Dict[str, Any]) -> str:
    """语义核 dict → **settings 列**稳定哈希（SHA256 hex）。"""
    return _stable_sha256(
        {
            "v": 1,
            "kind": "strategy_workbench_settings_core",
            "settings_core": dict(semantic_core_payload or {}),
        }
    )


def to_env_hash(
    *,
    strategy_name: str,
    stock_ids: Sequence[str],
    start_date: str,
    end_date: str,
    run_mode: str,
    engine_version: str,
    worker_module_path: str = "",
    worker_class_name: str = "",
    worker_code_hash: str = "",
    data_contract_mapping: str = "",
) -> str:
    """env 因子 → **env 列**稳定哈希（内部先 ``env_fingerprint_payload`` 再 SHA256）。"""
    from .env_resolver import env_fingerprint_payload

    return _stable_sha256(
        env_fingerprint_payload(
            strategy_name=strategy_name,
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
            run_mode=run_mode,
            engine_version=engine_version,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_code_hash=worker_code_hash,
            data_contract_mapping=data_contract_mapping,
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
    """一次解析结果：语义 settings、规范化快照、env 切片与 ``(settings_fp, env_fp)``。"""

    validated_settings: Any
    normalized_settings_dict: Dict[str, Any]
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
    raw_settings: Dict[str, Any],
    stock_ids: List[str],
    latest_completed_trading_date: str,
) -> Optional[DbCacheFingerprintResolution]:
    """
    ``raw_settings`` → 规范化快照 → env 因子 → ``settings_fp`` + ``env_fp``。

    ``stock_ids`` 须由调用方传入，与回测 flow build jobs 所用列表一致（不从 settings 推导）。
    ``latest_completed_trading_date`` 与 flow 一致，用于 env 日期窗（避免在此查日历 IO）。

    settings 不可用或 env/worker 解析失败时 ``None``。
    """
    from .env_resolver import resolve_env_inputs
    from .settings_resolver import validated_normalized_snapshot

    prepared = validated_normalized_snapshot(raw_settings)
    if prepared is None:
        return None
    validated_settings, normalized_settings_dict = prepared

    env = resolve_env_inputs(
        strategy_name=strategy_name,
        normalized_settings_dict=normalized_settings_dict,
        stock_ids=stock_ids,
        latest_completed_trading_date=latest_completed_trading_date,
    )
    if env is None:
        return None

    settings_fp, env_fp = _fingerprint_pair_from_env(
        validated_settings=validated_settings,
        strategy_name=strategy_name,
        env=env,
    )

    return DbCacheFingerprintResolution(
        validated_settings=validated_settings,
        normalized_settings_dict=normalized_settings_dict,
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
        start_date=env.env_start_date,
        end_date=env.env_end_date,
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
    start_date: str,
    end_date: str,
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

    from ..config import derive_run_mode, read_strategy_module_version
    from .settings_resolver import _require_valid_snapshot, strip_to_semantic_core

    if not isinstance(settings, _StrategySettings):
        raise TypeError("expected StrategySettings")
    snap = _require_valid_snapshot(settings)
    core = strip_to_semantic_core(snap)
    rm = run_mode if run_mode is not None else derive_run_mode(snap)
    ev = engine_version if engine_version is not None else read_strategy_module_version()
    return (
        to_settings_hash(core),
        to_env_hash(
            strategy_name=strategy_name,
            stock_ids=stock_ids,
            start_date=str(start_date),
            end_date=str(end_date),
            run_mode=str(rm),
            engine_version=str(ev),
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
    start_date: str,
    end_date: str,
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
            start_date=str(start_date),
            end_date=str(end_date),
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
