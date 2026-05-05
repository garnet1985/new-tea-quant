#!/usr/bin/env python3
"""
策略工作台 DB 缓存协调服务。

指纹算法在同包 ``finger_print``；本类只做规范化、查表、TTL/版本上限调度；表读写委托 ``persistence.snapshot_persist``。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from .persistence.snapshot_persist import (
    persist_enum_snapshot,
    persist_simulator_summary_patch,
    replace_enum_cache_by_fingerprints,
    strip_result_summary_keys_by_fingerprints,
)
from .settings import StrategySettingsService
from core.tables.ui_bff.strategy_workbench_snapshot.model import SysStrategyWorkbenchSnapshotModel

from . import finger_print
from .config import (
    CACHE_MAX_AGE,
    MAX_SNAPSHOT_ROWS_PER_STRATEGY,
    RESULT_KEY_CAPITAL_ALLOCATION,
    RESULT_KEY_ENUM,
    RESULT_KEY_PRICE_FACTOR,
    SIMULATOR_CAPITAL_ALLOCATION,
    SIMULATOR_ENUM,
    SIMULATOR_PRICE_FACTOR,
    derive_run_mode,
)


def _parse_datetime(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except Exception:
        return None


class DbCacheService:
    """协调 ``sys_strategy_workbench_snapshot`` 读写；不替代模拟器计算 summary。"""

    def __init__(self, model: Optional[SysStrategyWorkbenchSnapshotModel] = None) -> None:
        self._model = model or SysStrategyWorkbenchSnapshotModel()

    @staticmethod
    def build_strategy_settings(raw_settings: Dict[str, Any]) -> StrategySettings:
        """由任意来源 dict 构造 ``StrategySettings``（后续 ``validate`` / ``to_dict()``）。"""
        return StrategySettings(raw_settings=dict(raw_settings or {}))

    def fingerprint_pair(
        self,
        *,
        settings: StrategySettings,
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
        """生成 ``(settings_fp, env_fp)``，委托同包 ``finger_print``。"""
        return finger_print.db_cache_fingerprint_pair(
            settings=settings,
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

    @staticmethod
    def normalized_snapshot_dict(settings: StrategySettings) -> Dict[str, Any]:
        """校验通过后返回完整快照（写入 ``settings_snapshot`` 列）。"""
        report = settings.validate()
        if not report.is_usable():
            errs = [
                f'{item.get("field_path", "?")}: {item.get("message", "")}'
                for item in (report.errors or [])
                if item.get("level") == "critical"
            ]
            detail = "；".join(errs) if errs else "settings 校验未通过"
            raise ValueError(detail)
        return settings.to_dict()

    def row_is_expired(self, row: Dict[str, Any]) -> bool:
        """基于 ``updated_at`` 与 ``CACHE_MAX_AGE``。"""
        updated = _parse_datetime((row or {}).get("updated_at"))
        if updated is None:
            return True
        now = datetime.now(updated.tzinfo) if updated.tzinfo else datetime.now()
        return now - updated > CACHE_MAX_AGE

    def find_row_by_fingerprints(
        self,
        strategy_name: str,
        settings_fingerprint_id: str,
        env_fingerprint_id: str,
        *,
        delete_if_expired: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        按 **AND** 命中一行；若过期则删除并返回 ``None``。
        """
        sfp = str(settings_fingerprint_id or "").strip()
        efp = str(env_fingerprint_id or "").strip()
        if not sfp or not efp:
            return None
        rows = self._model.list_by_strategy_fingerprints(
            strategy_name,
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
            limit=1,
        )
        if not rows:
            return None
        row = rows[0]
        if self.row_is_expired(row):
            if delete_if_expired:
                sid = int((row or {}).get("version") or 0)
                if sid > 0:
                    self._model.delete_snapshot_row(strategy_name, sid)
            return None
        return row

    def prune_oldest_if_over_limit(self, strategy_name: str) -> None:
        """策略下行数超过 ``MAX_SNAPSHOT_ROWS_PER_STRATEGY`` 时删除 **version 最小** 的行直至达标。"""
        rows = self._model.list_versions_asc(strategy_name, limit=MAX_SNAPSHOT_ROWS_PER_STRATEGY + 50)
        while len(rows) > MAX_SNAPSHOT_ROWS_PER_STRATEGY:
            oldest = rows[0]
            sid = int((oldest or {}).get("version") or 0)
            if sid <= 0:
                break
            self._model.delete_snapshot_row(strategy_name, sid)
            rows = rows[1:]

    def generate_cache(
        self,
        simulator_name: str,
        strategy_name: str,
        raw_settings: Dict[str, Any],
        result_summary_patch: Dict[str, Any],
        *,
        stock_ids: Sequence[str],
        start_date: str,
        end_date: str,
        worker_module_path: str = "",
        worker_class_name: str = "",
        worker_code_hash: str = "",
        data_contract_mapping: str = "",
        force_refresh: bool = False,
        run_mode: Optional[str] = None,
        engine_version: Optional[str] = None,
        workbench_run_id: Optional[str] = None,
    ) -> int:
        """
        统一入口：按指纹写入 ``result_summary`` 中对应模拟器的数据。

        - **枚举器**（``simulator_name == SIMULATOR_ENUM``）：委托
          ``persistence.snapshot_persist.persist_enum_snapshot``；``result_summary_patch`` 为**单行**
          枚举摘要 dict（与Enumerator postprocess 首行一致），或包含 ``\"enum\"`` 键的外层 dict。
        - **价格 / 资金**：写入 ``result_summary`` 的 ``price_factor`` / ``capital_allocation``（``persist_simulator_summary_patch``）。
        - ``force_refresh``：按模拟器剥离对应键后再写入（枚举 ``replace_enum_cache_by_fingerprints``；价格 / 资金 ``strip_result_summary_keys_by_fingerprints``）。
        """
        settings = self.build_strategy_settings(dict(raw_settings or {}))
        normalized = DbCacheService.normalized_snapshot_dict(settings)
        rm = str(run_mode).strip() if run_mode else derive_run_mode(normalized)
        sfp, efp = self.fingerprint_pair(
            settings=settings,
            strategy_name=strategy_name,
            stock_ids=stock_ids,
            start_date=str(start_date),
            end_date=str(end_date),
            run_mode=rm,
            engine_version=engine_version,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_code_hash=worker_code_hash,
            data_contract_mapping=data_contract_mapping,
        )

        sim = str(simulator_name or "").strip().lower()
        if force_refresh:
            if sim == SIMULATOR_ENUM:
                replace_enum_cache_by_fingerprints(
                    strategy_name=str(strategy_name),
                    settings_finger_print_id=sfp,
                    env_fingerprint_id=efp,
                )
            elif sim == SIMULATOR_PRICE_FACTOR:
                strip_result_summary_keys_by_fingerprints(
                    strategy_name=str(strategy_name),
                    settings_finger_print_id=sfp,
                    env_fingerprint_id=efp,
                    keys=(RESULT_KEY_PRICE_FACTOR,),
                )
            elif sim == SIMULATOR_CAPITAL_ALLOCATION:
                strip_result_summary_keys_by_fingerprints(
                    strategy_name=str(strategy_name),
                    settings_finger_print_id=sfp,
                    env_fingerprint_id=efp,
                    keys=(RESULT_KEY_CAPITAL_ALLOCATION,),
                )

        patch = dict(result_summary_patch or {})

        if sim == SIMULATOR_ENUM:
            first_row = patch.get(RESULT_KEY_ENUM) if isinstance(patch.get(RESULT_KEY_ENUM), dict) else patch
            api_settings = StrategySettingsService.runtime_to_api(dict(normalized))
            if not api_settings:
                api_settings = dict(normalized)
            sid = persist_enum_snapshot(
                strategy_name,
                settings_snapshot_api=api_settings,
                enum_summary_first_row=dict(first_row or {}),
                settings_fingerprint_id=sfp,
                env_fingerprint_id=efp,
                workbench_run_id=workbench_run_id,
            )
            sid = int(sid or 0)
            if sid > 0:
                self.prune_oldest_if_over_limit(strategy_name)
            return sid

        if sim == SIMULATOR_PRICE_FACTOR:
            inner = (
                patch[RESULT_KEY_PRICE_FACTOR]
                if RESULT_KEY_PRICE_FACTOR in patch
                else patch
            )
            api_settings = StrategySettingsService.runtime_to_api(dict(normalized))
            if not api_settings:
                api_settings = dict(normalized)
            sid = persist_simulator_summary_patch(
                strategy_name,
                settings_snapshot_api=api_settings,
                result_key=RESULT_KEY_PRICE_FACTOR,
                patch_value=inner,
                settings_finger_print_id=sfp,
                env_fingerprint_id=efp,
            )
            sid = int(sid or 0)
            if sid > 0:
                self.prune_oldest_if_over_limit(strategy_name)
            return sid

        if sim == SIMULATOR_CAPITAL_ALLOCATION:
            inner = (
                patch[RESULT_KEY_CAPITAL_ALLOCATION]
                if RESULT_KEY_CAPITAL_ALLOCATION in patch
                else patch
            )
            api_settings = StrategySettingsService.runtime_to_api(dict(normalized))
            if not api_settings:
                api_settings = dict(normalized)
            sid = persist_simulator_summary_patch(
                strategy_name,
                settings_snapshot_api=api_settings,
                result_key=RESULT_KEY_CAPITAL_ALLOCATION,
                patch_value=inner,
                settings_finger_print_id=sfp,
                env_fingerprint_id=efp,
            )
            sid = int(sid or 0)
            if sid > 0:
                self.prune_oldest_if_over_limit(strategy_name)
            return sid

        raise ValueError(f"未知的 simulator_name: {simulator_name!r}")


__all__ = ["DbCacheService"]
