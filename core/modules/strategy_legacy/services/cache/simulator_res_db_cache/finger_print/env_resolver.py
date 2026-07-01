#!/usr/bin/env python3
"""
**Env 步骤层**：在已有 **规范化 settings 快照** 上，收集并组装 **env 指纹载荷 dict**（再由 ``finger_print`` 做 SHA256）。

含 universe（``stock_ids``，规范化排序）、run_mode、系统版本、worker 三联、``data_contract_mapping``；日历窗仅用于 flow 运行，**不入 env 载荷**。
实现内联在此模块（原 ``orchestration.write.resolve_*``）。
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from core.infra.project_context import ProjectContext

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
    resolve_backtest_date_range,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_info,
    resolve_worker_ref,
)
from core.system import get_version

from ..config import derive_run_mode


class ResolveEnv:
    """env 指纹侧字段解析（无实例状态）。不写回用户持久化 settings；日期仅用副本/fallback。"""

    @staticmethod
    def date_range_for_fingerprint(
        *,
        strategy_name: str,
        normalized_settings_dict: Dict[str, Any],
        stock_list: Sequence[str],
        latest_completed_trading_date: str,
        data_manager: Optional[Any] = None,
    ) -> Tuple[str, str]:
        """
        与回测 flow 一致的日历窗：``sampling`` → 样本最早 K 线 → 默认起点；空 ``end_date`` 用调用方 ``latest_completed_trading_date``。

        ``stock_list`` 须与本次 flow / build_jobs 使用的列表一致。
        """
        _ = strategy_name
        view = StrategySettingsView.from_dict(dict(normalized_settings_dict or {}))
        period = resolve_backtest_date_range(
            settings_view=view,
            stock_ids=stock_list,
            latest_completed_trading_date=str(latest_completed_trading_date or "").strip(),
            data_manager=data_manager,
        )
        return period.as_tuple()

    @staticmethod
    def worker_code_identity(*, strategy_name: str) -> Dict[str, str]:
        """
        **用户 Worker 实现身份**：策略目录对应的 Worker **模块路径 / 类名 / 源文件 SHA256**。

        与枚举指纹路径一致：``load_strategy_info`` → ``resolve_worker_ref`` → import 模块后对 **模块源文件** 哈希。
        返回键：``worker_module_path``、``worker_class_name``、``worker_code_hash``。
        """
        strategy_info = load_strategy_info(strategy_name)
        worker_module_path, worker_class_name, worker_file_path = resolve_worker_ref(
            strategy_name,
            strategy_info=strategy_info,
        )
        mod_path = str(worker_module_path or "").strip()
        cls_name = str(worker_class_name or "").strip()
        worker_code_hash = ""
        file_path = str(worker_file_path or "").strip()
        if file_path:
            try:
                worker_code_hash = ResolveEnv._hash_file(Path(file_path))
            except Exception:
                worker_code_hash = ""
        return {
            "worker_module_path": mod_path,
            "worker_class_name": cls_name,
            "worker_code_hash": worker_code_hash,
        }

    @staticmethod
    def _hash_file(path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def data_contract_mapping() -> str:
        """
        契约 **mapping 层** 指纹（与 env 载荷字段 ``data_contract_mapping`` 对齐）。

        仅包含 **core** / **userspace** 的 ``data_contract`` mapping 源文件 SHA256，再合成一层 hex。
        用户 ``settings['data']`` 已由 **settings 语义核 / settings_fp** 跟踪，此处 **不再混入**，避免与 settings 侧重复计义。
        """
        core_mapping_hash = ""
        try:
            dc_mapping_module = importlib.import_module("core.modules.data_contract.mapping")
            dc_mapping_file = inspect.getsourcefile(dc_mapping_module)
            if dc_mapping_file:
                core_mapping_hash = ResolveEnv._hash_file(Path(dc_mapping_file))
        except Exception:
            core_mapping_hash = ""

        userspace_mapping_hash = ""
        userspace_mapping_file = ProjectContext.path.get_data_contract_mapping_path()
        if userspace_mapping_file.exists():
            userspace_mapping_hash = ResolveEnv._hash_file(Path(userspace_mapping_file))

        payload = {
            "core_mapping_hash": core_mapping_hash,
            "userspace_mapping_hash": userspace_mapping_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _collect_stock_ids(stock_list: List[str]) -> List[str]:
        return sorted({str(sid) for sid in stock_list if sid})


    @staticmethod
    def resolve_env_inputs(
        *,
        strategy_name: str,
        normalized_settings_dict: Dict[str, Any],
        stock_list: List[str],
        latest_completed_trading_date: str,
        data_manager: Optional[Any] = None,
        env_start_date: str = "",
        env_end_date: str = "",
    ) -> Optional[EnvFingerprintInputs]:
        """
        由已通过校验的规范化快照解析 env。

        ``stock_list`` 须与本次回测 / 枚举 flow 在 build jobs 阶段使用的列表一致（不由 settings 推导）。
        ``latest_completed_trading_date`` 须与 flow 侧解析的最新已完成交易日一致（用于空 ``end_date`` fallback）。
        若调用方已解析 ``env_start_date`` / ``env_end_date``（与 flow 一致），则不再查库。
        Worker 身份解析失败时返回 ``None``。
        """
        stock_ids = ResolveEnv._collect_stock_ids(stock_list)
        preset_start = str(env_start_date or "").strip()
        preset_end = str(env_end_date or "").strip()
        if preset_start and preset_end:
            resolved_start, resolved_end = preset_start, preset_end
        else:
            resolved_start, resolved_end = ResolveEnv.date_range_for_fingerprint(
                strategy_name=strategy_name,
                normalized_settings_dict=normalized_settings_dict,
                stock_list=stock_list,
                latest_completed_trading_date=latest_completed_trading_date,
                data_manager=data_manager,
            )
        run_mode = derive_run_mode(normalized_settings_dict)
        engine_version = get_version()

        try:
            worker = ResolveEnv.worker_code_identity(strategy_name=strategy_name)
        except Exception:
            return None

        data_contract_mapping = ResolveEnv.data_contract_mapping()

        return EnvFingerprintInputs(
            stock_ids=stock_ids,
            env_start_date=resolved_start,
            env_end_date=resolved_end,
            run_mode=run_mode,
            engine_version=engine_version,
            worker_module_path=worker["worker_module_path"],
            worker_class_name=worker["worker_class_name"],
            worker_code_hash=worker["worker_code_hash"],
            data_contract_mapping=data_contract_mapping,
        )

    @staticmethod
    def resolve_storage_database_type() -> str:
        """当前 ``userspace/config/database/common.json`` 的 ``database_type``（mysql / duckdb 等）。"""
        cfg = ProjectContext.config.load_database_config()
        return str(cfg.get("database_type") or "").strip().lower()

    @staticmethod
    def env_fingerprint_payload(
        *,
        strategy_name: str,
        stock_ids: Sequence[str],
        run_mode: str,
        engine_version: str,
        worker_module_path: str = "",
        worker_class_name: str = "",
        worker_code_hash: str = "",
        data_contract_mapping: str = "",
        database_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        组装 env 指纹 **载荷 dict**（``v=6``），**不含** settings 语义核与日历窗。

        回测 scope 以规范化后的 ``stock_ids`` 列表为准（与 ``compute_scope_fingerprint_id`` 同源列表）。
        ``database_type`` 纳入 env，避免 MySQL ↔ DuckDB 切换后仍命中旧快照。
        """
        normalized_stock_ids = ResolveEnv._collect_stock_ids(list(stock_ids))
        db_type = (
            str(database_type or "").strip().lower()
            or ResolveEnv.resolve_storage_database_type()
        )
        return {
            "v": 6,
            "kind": "strategy_db_cache_env",
            "strategy_name": str(strategy_name),
            "stock_ids": normalized_stock_ids,
            "run_mode": str(run_mode),
            "engine_version": str(engine_version),
            "database_type": db_type,
            "worker_module_path": str(worker_module_path),
            "worker_class_name": str(worker_class_name),
            "worker_code_hash": str(worker_code_hash),
            "data_contract_mapping": str(data_contract_mapping),
        }

class EnvFingerprintInputs(NamedTuple):
    """供 DbCache env 指纹与 ``generate_cache`` 使用的 env 切片。"""

    stock_ids: List[str]
    env_start_date: str
    env_end_date: str
    run_mode: str
    engine_version: str
    worker_module_path: str
    worker_class_name: str
    worker_code_hash: str
    data_contract_mapping: str


def resolve_env_inputs(**kwargs: Any) -> Optional[EnvFingerprintInputs]:
    """模块级入口（与 ``ResolveEnv.resolve_env_inputs`` 等价）。"""
    return ResolveEnv.resolve_env_inputs(**kwargs)


def env_fingerprint_payload(**kwargs: Any) -> Dict[str, Any]:
    """模块级入口（与 ``ResolveEnv.env_fingerprint_payload`` 等价）。"""
    return ResolveEnv.env_fingerprint_payload(**kwargs)


__all__ = [
    "EnvFingerprintInputs",
    "ResolveEnv",
    "env_fingerprint_payload",
    "resolve_env_inputs",
]