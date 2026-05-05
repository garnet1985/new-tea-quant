#!/usr/bin/env python3
"""
Simulator Res DB Cache：校验并标准化 settings → 计算指纹 → 读/写 ``result_report``。

表访问（双指纹命中、``result_report`` 槽位合并）在 ``SimulatorResDbCacheService`` 私有方法内；指纹数学在 ``finger_print``。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.enums import Simulator

from . import finger_print
from .finger_print.finger_print import DbCacheFingerprintResolution
from .config import MAX_SNAPSHOT_ROWS_PER_STRATEGY
from core.modules.data_manager import DataManager


class SimulatorResDbCacheService:
    def __init__(self) -> None:
        data_mgr = DataManager()
        self.table_operator = data_mgr.get_table("sys_strategy_workbench_snapshot")

    def set_cache(
        self,
        strategy_name: str,
        settings_snapshot: Dict[str, Any],
        result_report: Dict[str, Any],
        settings_fingerprint_id: str,
        env_fingerprint_id: str,
    ) -> int:
        
        version = self._generate_version(strategy_name)

        return version


    def _generate_version(self, strategy_name: str) -> int:
        pass

    def load_cache_by_fingerprints(
        self,
        strategy_name: str,
        settings_fingerprint_id: str,
        env_fingerprint_id: str,
    ) -> Dict[str, Any]:
        pass

    def load_cache_by_version(
        self,
        strategy_name: str,
        version: int,
    ) -> Dict[str, Any]:
        pass

    def load_latest_cache_for_strategy(
        self,
        strategy_name: str,
    ) -> Dict[str, Any]:
        pass


    def backup_settings_file_for_strategy(self, strategy_name: str) -> None:
        pass

    def write_settings_file_for_strategy(self, strategy_name: str, settings: Dict[str, Any], pretty: bool) -> None:
        pass

    def clean_up_cache(self) -> None:
        # self._delete_cache_if_over_days_or_limit()
        pass

    def delete_cache_by_version(self, strategy_name: str, version: int) -> bool:
        pass

    def delete_cache_for_strategy(self, strategy_name: str) -> bool:
        pass



    # def _lookup_enum_cache(
    #     self,
    #     strategy_name: str,
    #     settings_finger_print_id: str,
    #     env_fingerprint_id: str,
    # ) -> Optional[Tuple[List[Dict[str, Any]], int]]:
    #     """
    #     双指纹命中后，读出 ``result_report`` 里键 ``"enum"`` 的值。

    #     **契约**：槽位只存 **dict**。命中返回 ``([dict], snapshot_id)``（外层 list 仅为枚举流水线接口形状）；否则 ``None``。
    #     """
    #     rows = self.table_operator.list_by_strategy_fingerprints(
    #         strategy_name,
    #         settings_finger_print_id=str(settings_finger_print_id or "").strip(),
    #         env_fingerprint_id=str(env_fingerprint_id or "").strip(),
    #         limit=1,
    #     )
    #     if not rows:
    #         return None
    #     row = rows[0]
    #     snapshot_id = int((row or {}).get("snapshot_id") or 0)
    #     rr = dict((row or {}).get("result_report") or {})
    #     enum_raw = rr.get("enum")
    #     if not isinstance(enum_raw, dict):
    #         return None
    #     if not enum_raw:
    #         return None
    #     return ([enum_raw], snapshot_id)

#     def _persist_enum_snapshot(
#         self,
#         strategy_name: str,
#         *,
#         settings_snapshot_api: Dict[str, Any],
#         report_enum: Dict[str, Any],
#         settings_fingerprint_id: str,
#         env_fingerprint_id: str,
#     ) -> int:
#         """写入 / 合并 ``result_report["enum"]``。"""
#         payload = dict(report_enum or {})
#         if not payload:
#             return 0

#         rows = self.table_operator.list_by_strategy_fingerprints(
#             strategy_name,
#             settings_finger_print_id=str(settings_fingerprint_id or "").strip(),
#             env_fingerprint_id=str(env_fingerprint_id or "").strip(),
#             limit=1,
#         )
#         if rows:
#             sid = int((rows[0] or {}).get("snapshot_id") or 0)
#             if sid <= 0:
#                 return 0
#             rr = dict((rows[0] or {}).get("result_report") or {})
#             rr["enum"] = payload
#             self.table_operator.update_result_report(
#                 strategy_name,
#                 sid,
#                 rr,
#                 settings_finger_print_id=str(settings_fingerprint_id or ""),
#                 env_fingerprint_id=str(env_fingerprint_id or ""),
#             )
#             return sid

#         created = self.table_operator.create_snapshot(
#             strategy_name,
#             settings_snapshot_api or {},
#             {"enum": payload},
#             settings_finger_print_id=str(settings_fingerprint_id or ""),
#             env_fingerprint_id=str(env_fingerprint_id or ""),
#         )
#         return int((created or {}).get("snapshot_id") or 0)

#     def _persist_result_report_slot(
#         self,
#         strategy_name: str,
#         *,
#         settings_snapshot_api: Dict[str, Any],
#         result_key: str,
#         report_slot: Dict[str, Any],
#         settings_fingerprint_id: str,
#         env_fingerprint_id: str,
#     ) -> int:
#         """写入 / 合并 ``result_report[result_key]``（如 ``price_factor`` / ``capital_allocation``）。"""
#         slot = dict(report_slot or {})
#         if not slot:
#             return 0
#         key = str(result_key or "").strip()
#         if not key:
#             return 0

#         rows = self.table_operator.list_by_strategy_fingerprints(
#             strategy_name,
#             settings_finger_print_id=str(settings_fingerprint_id or "").strip(),
#             env_fingerprint_id=str(env_fingerprint_id or "").strip(),
#             limit=1,
#         )
#         if rows:
#             sid = int((rows[0] or {}).get("snapshot_id") or 0)
#             if sid <= 0:
#                 return 0
#             rr = dict((rows[0] or {}).get("result_report") or {})
#             rr[key] = slot
#             self.table_operator.update_result_report(
#                 strategy_name,
#                 sid,
#                 rr,
#                 settings_finger_print_id=str(settings_fingerprint_id or ""),
#                 env_fingerprint_id=str(env_fingerprint_id or ""),
#             )
#             return sid

#         created = self.table_operator.create_snapshot(
#             strategy_name,
#             settings_snapshot_api or {},
#             {key: slot},
#             settings_finger_print_id=str(settings_fingerprint_id or ""),
#             env_fingerprint_id=str(env_fingerprint_id or ""),
#         )
#         return int((created or {}).get("snapshot_id") or 0)

#     @staticmethod
#     def lookup_enum_rows(
#         strategy_name: str,
#         settings_finger_print_id: str,
#         env_fingerprint_id: str,
#     ) -> Optional[Tuple[List[Dict[str, Any]], int]]:
#         return SimulatorResDbCacheService()._lookup_enum_cache(
#             strategy_name,
#             str(settings_finger_print_id or "").strip(),
#             str(env_fingerprint_id or "").strip(),
#         )

#     @staticmethod
#     def build_strategy_settings(raw_settings: Dict[str, Any]) -> StrategySettings:
#         return StrategySettings(raw_settings=dict(raw_settings or {}))

#     def fingerprint_pair(
#         self,
#         *,
#         settings: StrategySettings,
#         strategy_name: str,
#         stock_ids: Sequence[str],
#         start_date: str,
#         end_date: str,
#         run_mode: Optional[str] = None,
#         engine_version: Optional[str] = None,
#         worker_module_path: str = "",
#         worker_class_name: str = "",
#         worker_code_hash: str = "",
#         data_contract_mapping: str = "",
#     ) -> Tuple[str, str]:
#         return finger_print.db_cache_fingerprint_pair(
#             settings=settings,
#             strategy_name=str(strategy_name),
#             stock_ids=stock_ids,
#             start_date=start_date,
#             end_date=end_date,
#             run_mode=run_mode,
#             engine_version=engine_version,
#             worker_module_path=worker_module_path,
#             worker_class_name=worker_class_name,
#             worker_code_hash=worker_code_hash,
#             data_contract_mapping=data_contract_mapping,
#         )

#     @staticmethod
#     def normalized_snapshot_dict(settings: StrategySettings) -> Dict[str, Any]:
#         report = settings.validate()
#         if not report.is_usable():
#             errs = [
#                 f'{item.get("field_path", "?")}: {item.get("message", "")}'
#                 for item in (report.errors or [])
#                 if item.get("level") == "critical"
#             ]
#             detail = "；".join(errs) if errs else "settings 校验未通过"
#             raise ValueError(detail)
#         return settings.to_dict()

#     def prune_oldest_if_over_limit(self, strategy_name: str) -> None:
#         rows = self.table_operator.list_versions_asc(strategy_name, limit=MAX_SNAPSHOT_ROWS_PER_STRATEGY + 50)
#         while len(rows) > MAX_SNAPSHOT_ROWS_PER_STRATEGY:
#             oldest = rows[0]
#             sid = int((oldest or {}).get("version") or 0)
#             if sid <= 0:
#                 break
#             self.table_operator.delete_snapshot_row(strategy_name, sid)
#             rows = rows[1:]

#     def _persist_sid(self, strategy_name: str, sid: int) -> int:
#         sid = int(sid or 0)
#         if sid > 0:
#             self.prune_oldest_if_over_limit(strategy_name)
#         return sid

#     def upsert_simulator_cache_row(
#         self,
#         *,
#         resolved: DbCacheFingerprintResolution,
#         simulator: Simulator,
#         strategy_name: str,
#         partial_result_report: Dict[str, Any],
#     ) -> int:
#         """
#         在 Step 1 已有 ``resolved`` 的前提下：``normalized_settings_dict`` 已为规范化快照，直接作 ``settings_snapshot``；
#         再按模拟器类型写入表列 ``result_report`` 中 **对应槽位**。

#         ``partial_result_report``：仅 **一种** 入参——本步摘要 dict，且与落库后 ``result_report`` 中 **该步槽位**
#         （键 ``"enum"`` / ``"price_factor"`` / ``"capital_allocation"``）内 JSON **完全一致**。不做其它形状的解析或兜底。
#         """
#         settings_snapshot = dict(resolved.normalized_settings_dict or {})
#         sfp = resolved.settings_fp
#         efp = resolved.env_fp
#         step_report = dict(partial_result_report or {})

#         if simulator == Simulator.ENUMERATOR:
#             sid = self._persist_enum_snapshot(
#                 strategy_name,
#                 settings_snapshot_api=settings_snapshot,
#                 report_enum=step_report,
#                 settings_fingerprint_id=sfp,
#                 env_fingerprint_id=efp,
#             )
#             return self._persist_sid(strategy_name, sid)

#         if simulator == Simulator.PRICE_FACTOR:
#             sid = self._persist_result_report_slot(
#                 strategy_name,
#                 settings_snapshot_api=settings_snapshot,
#                 result_key="price_factor",
#                 report_slot=step_report,
#                 settings_fingerprint_id=sfp,
#                 env_fingerprint_id=efp,
#             )
#             return self._persist_sid(strategy_name, sid)

#         if simulator == Simulator.CAPITAL_ALLOCATION:
#             sid = self._persist_result_report_slot(
#                 strategy_name,
#                 settings_snapshot_api=settings_snapshot,
#                 result_key="capital_allocation",
#                 report_slot=step_report,
#                 settings_fingerprint_id=sfp,
#                 env_fingerprint_id=efp,
#             )
#             return self._persist_sid(strategy_name, sid)

#         raise ValueError(f"未知的 simulator: {simulator!r}")


# DbCacheService = SimulatorResDbCacheService

# __all__ = ["DbCacheService", "SimulatorResDbCacheService"]


# def lookup_enum_cache(
#     strategy_name: str,
#     settings_finger_print_id: str,
#     env_fingerprint_id: str,
# ) -> Optional[Tuple[List[Dict[str, Any]], int]]:
#     """模块级入口（惰性导出）：等价于 ``SimulatorResDbCacheService.lookup_enum_rows``。"""
#     return SimulatorResDbCacheService.lookup_enum_rows(
#         strategy_name,
#         settings_finger_print_id,
#         env_fingerprint_id,
#     )


# def persist_enum_snapshot(
#     strategy_name: str,
#     *,
#     settings_snapshot_api: Dict[str, Any],
#     report_enum: Dict[str, Any],
#     settings_fingerprint_id: str,
#     env_fingerprint_id: str,
# ) -> int:
#     """模块级入口（惰性导出）：委托 ``SimulatorResDbCacheService._persist_enum_snapshot``。"""
#     return SimulatorResDbCacheService()._persist_enum_snapshot(
#         strategy_name,
#         settings_snapshot_api=settings_snapshot_api,
#         report_enum=report_enum,
#         settings_fingerprint_id=settings_fingerprint_id,
#         env_fingerprint_id=env_fingerprint_id,
#     )
