# """枚举数据层：contract 批量物化、单实体加载、GLOBAL 预热。"""
# from __future__ import annotations

# import logging
# from dataclasses import dataclass, field
# from typing import Any, Dict, Hashable, List, Mapping, Optional, Sequence, Tuple

# from core.modules.data_contract import DataContracts
# from core.modules.data_contract.contracts import ContractScope, DataKey
# from core.modules.data_contract.contracts import DataContract
# from core.modules.data_contract.contracts import IssueResult
# from core.modules.indicator import IndicatorService
# from core.utils.date.date_utils import DateUtils

# from .strategy_data_config import StrategyDataConfig

# logger = logging.getLogger(__name__)

# _MAX_LOOKBACK_DAYS = 60


# @dataclass
# class EntityContractBatch:
#     """一次 dispatch job 内多 entity 的 contract 物化结果。"""

#     global_contracts: Dict[DataKey, DataContract] = field(default_factory=dict)
#     per_entity_results: Dict[DataKey, IssueResult] = field(default_factory=dict)

#     @classmethod
#     def hydrate(
#         cls,
#         *,
#         entity_ids: Sequence[str],
#         settings: Dict[str, Any],
#         start: str,
#         end: str,
#         global_data: Optional[Mapping[str, Any]] = None,
#         fresh_strategy_cache: bool = False,
#     ) -> EntityContractBatch:
#         return cls.batch_load(
#             entity_ids=entity_ids,
#             settings=settings,
#             start=start,
#             end=end,
#             global_data=global_data,
#             fresh_strategy_cache=fresh_strategy_cache,
#         )

#     @classmethod
#     def batch_load(
#         cls,
#         *,
#         entity_ids: Sequence[str],
#         settings: Dict[str, Any],
#         start: str,
#         end: str,
#         global_data: Optional[Mapping[str, Any]] = None,
#         fresh_strategy_cache: bool = False,
#     ) -> EntityContractBatch:
#         """批量装载：一次 IO 读本 job 内全部 entity 的 contract 数据。"""
#         ids = [str(x).strip() for x in entity_ids if str(x).strip()]
#         if not ids:
#             raise ValueError("EntityContractBatch.batch_load 需要非空 entity_ids")

#         if fresh_strategy_cache:
#             DataContracts.shared_cache().enter_strategy_run()

#         data_config = StrategyDataConfig(settings)
#         dcm = DataContracts()
#         batch = cls()
#         base_key = DataKey(str(data_config.normalize_base(data_config.base)["data_key"]))

#         for raw in data_config.issue_declarations():
#             item = data_config.normalize_declaration_item(raw)
#             dk = DataKey(str(item["data_key"]))
#             params = dict(item.get("params") or {})
#             spec = dcm.map.get(dk)
#             if spec is None:
#                 raise ValueError(f"未注册的 data_key：{dk.value}")

#             scope = spec.get("scope")
#             if scope == ContractScope.GLOBAL:
#                 slot = StrategyDataConfig.storage_key_for(dk, is_base=(dk == base_key))
#                 preloaded = (
#                     global_data is not None
#                     and slot in global_data
#                     and isinstance(global_data[slot], list)
#                 )
#                 if preloaded:
#                     contract = dcm.issue(
#                         dk,
#                         start=start,
#                         end=end,
#                         data=list(global_data[slot]),
#                         **params,
#                     ).require_contract()
#                 else:
#                     contract = dcm.issue(dk, start=start, end=end, **params).require_contract()
#                 batch.global_contracts[dk] = contract
#                 continue

#             if dk in batch.per_entity_results:
#                 raise ValueError(f"data 声明中重复的 data_key：{dk.value!r}")
#             batch.per_entity_results[dk] = dcm.issue(
#                 dk,
#                 entity_ids=ids,
#                 start=start,
#                 end=end,
#                 **params,
#             )

#         return batch

#     def contracts_for_entity(self, entity_id: str) -> Dict[DataKey, DataContract]:
#         eid = str(entity_id).strip()
#         if not eid:
#             raise ValueError("contracts_for_entity 需要非空 entity_id")

#         out: Dict[DataKey, DataContract] = dict(self.global_contracts)
#         for dk, result in self.per_entity_results.items():
#             out[dk] = result.entity(eid)
#         return out


# class EntityDataLoader:
#     """单实体 contract 数据加载与 DataCursor 视图。"""

#     def __init__(
#         self,
#         *,
#         stock_id: str,
#         settings: Dict[str, Any],
#         global_data: Optional[Dict[str, Any]] = None,
#     ) -> None:
#         self.stock_id = str(stock_id).strip()
#         if not self.stock_id:
#             raise ValueError("EntityDataLoader 缺少 stock_id")
#         self.settings = dict(settings or {})
#         self.global_data = dict(global_data or {})
#         self._data_config = StrategyDataConfig(self.settings)
#         self._contract_manager = DataContracts()
#         self._rows_by_slot: Dict[str, List[Dict[str, Any]]] = {}
#         self._cursor_contracts: Dict[DataKey, DataContract] = {}
#         self._cursor_name = f"entity:{self.stock_id}"
#         self._base_key = DataKey(str(self._data_config.normalize_base(self._data_config.base)["data_key"]))

#     @staticmethod
#     def min_required_records(settings: Dict[str, Any]) -> int:
#         return StrategyDataConfig(settings).min_required_records

#     @staticmethod
#     def enumeration_actual_start_date(start_date: str, min_required_records: int) -> str:
#         lookback_days = min(min_required_records, _MAX_LOOKBACK_DAYS)
#         try:
#             return DateUtils.sub_days(start_date, int(lookback_days * 1.5))
#         except Exception:
#             return start_date

#     def load(
#         self,
#         start_date: str,
#         end_date: str,
#         *,
#         job_batch: Optional[EntityContractBatch] = None,
#         fresh_strategy_cache: bool = True,
#     ) -> None:
#         if job_batch is not None:
#             self.attach_from_batch(job_batch, start_date=start_date, end_date=end_date)
#             return
#         if fresh_strategy_cache:
#             DataContracts.shared_cache().enter_strategy_run()
#         contracts = self._issue_single_entity_contracts(start_date, end_date)
#         self._apply_contracts_to_slots(contracts, start_date=start_date, end_date=end_date)
#         self._apply_indicators()
#         self._rebuild_cursor()

#     def attach_from_batch(
#         self,
#         job_batch: EntityContractBatch,
#         *,
#         start_date: str,
#         end_date: str,
#     ) -> None:
#         """从 job init 批量装载结果挂接数据并建 cursor（不再单独打 DB）。"""
#         contracts = job_batch.contracts_for_entity(self.stock_id)
#         self._apply_contracts_to_slots(contracts, start_date=start_date, end_date=end_date)
#         self._apply_indicators()
#         self._rebuild_cursor()

#     def get_base_series(self) -> List[Dict[str, Any]]:
#         """Base 时序（``data.base.data_key``）全量 rows。"""
#         return list(self._rows_by_slot.get(self._base_key.value) or [])

#     def data_until(self, date_of_today: str) -> Dict[str, Any]:
#         raw = self._contract_manager.until_cursor(self._cursor_name, date_of_today)
#         return self._hook_data_from_until_view(raw)

#     def _hook_data_from_until_view(
#         self,
#         raw: Mapping[Hashable, Any],
#     ) -> Dict[str, Any]:
#         """Map until_cursor sources (DataKey) → hook keys (data_key.value)."""
#         out: Dict[str, Any] = {}
#         for source, rows in raw.items():
#             slot = self._hook_slot_for_source(source)
#             if isinstance(rows, list):
#                 out[slot] = rows
#             else:
#                 out[slot] = list(rows) if rows is not None else []
#         return out

#     def _hook_slot_for_source(self, source: Hashable) -> str:
#         if isinstance(source, DataKey):
#             return source.value
#         return str(source)

#     def clear_working_state(self) -> None:
#         self._rows_by_slot = {}
#         self._cursor_contracts = {}
#         try:
#             self._contract_manager.close_until_cursor(self._cursor_name)
#         except Exception:
#             pass

#     def _issue_single_entity_contracts(
#         self,
#         start_date: str,
#         end_date: str,
#     ) -> Dict[DataKey, DataContract]:
#         out: Dict[DataKey, DataContract] = {}
#         dcm = self._contract_manager

#         for raw in self._data_config.issue_declarations():
#             item = self._data_config.normalize_declaration_item(raw)
#             dk = DataKey(str(item["data_key"]))
#             params = dict(item.get("params") or {})
#             spec = dcm.map.get(dk)
#             if spec is None:
#                 raise ValueError(f"未注册的 data_key：{dk.value}")

#             scope = spec.get("scope")
#             if scope == ContractScope.GLOBAL:
#                 contract = dcm.issue(dk, start=start_date, end=end_date, **params).require_contract()
#             else:
#                 contract = dcm.issue(
#                     dk,
#                     entity_id=self.stock_id,
#                     start=start_date,
#                     end=end_date,
#                     **params,
#                 ).require_contract()

#             if dk in out:
#                 raise ValueError(f"data 声明中重复的 data_key：{dk.value!r}")
#             out[dk] = contract
#         return out

#     def _apply_contracts_to_slots(
#         self,
#         contracts: Dict[DataKey, DataContract],
#         *,
#         start_date: str,
#         end_date: str,
#     ) -> None:
#         dcm = self._contract_manager
#         self._rows_by_slot = {}
#         self._cursor_contracts = {}

#         for dk, contract in contracts.items():
#             spec = dcm.map.get(dk)
#             slot = StrategyDataConfig.storage_key_for(dk, is_base=(dk == self._base_key))

#             if (
#                 spec
#                 and spec.get("scope") == ContractScope.GLOBAL
#                 and slot in self.global_data
#                 and isinstance(self.global_data[slot], list)
#             ):
#                 rows = list(self.global_data[slot])
#                 contract.data = rows
#             elif contract.needs_load:
#                 contract.load(start=start_date, end=end_date)
#                 rows = list(contract.data or [])
#             else:
#                 rows = list(contract.data or [])

#             self._rows_by_slot[slot] = rows
#             self._cursor_contracts[dk] = contract

#     def _apply_indicators(self) -> None:
#         for raw in self._data_config.issue_declarations():
#             item = self._data_config.normalize_declaration_item(raw)
#             indicators_cfg = StrategyDataConfig.normalize_indicators(item.get("indicators"))
#             if not indicators_cfg:
#                 continue
#             dk = DataKey(str(item["data_key"]))
#             slot = StrategyDataConfig.storage_key_for(dk, is_base=(dk == self._base_key))
#             rows = self._rows_by_slot.get(slot) or []
#             if not rows:
#                 continue
#             self._apply_indicators_to_rows(rows, indicators_cfg)

#     def _apply_indicators_to_rows(
#         self,
#         rows: List[Dict[str, Any]],
#         indicators_cfg: Dict[str, Any],
#     ) -> None:
#         for name, cfg, result in IndicatorService.compute_batch(rows, indicators_cfg):
#             try:
#                 if isinstance(result, list):
#                     field = self._indicator_field_name(name, cfg)
#                     for rec, val in zip(rows, result):
#                         rec[field] = val
#                 elif isinstance(result, dict):
#                     for key, series in result.items():
#                         field = self._indicator_field_name(f"{name}_{key}", cfg)
#                         for rec, val in zip(rows, series):
#                             rec[field] = val
#             except Exception as exc:
#                 logger.error(
#                     "写入指标失败: stock=%s indicator=%s error=%s",
#                     self.stock_id,
#                     name,
#                     exc,
#                 )

#     @staticmethod
#     def _indicator_field_name(name: str, params: Dict[str, Any]) -> str:
#         name = name.lower()
#         if not params:
#             return name
#         parts = [name]
#         for key in sorted(params.keys()):
#             parts.append(f"{key}{params[key]}")
#         return "_".join(str(p) for p in parts)

#     def _rebuild_cursor(self) -> None:
#         if not self._cursor_contracts:
#             raise ValueError("当前无可用 contract，无法构建 DataCursor")
#         self._contract_manager.open_until_cursor(
#             self._cursor_name,
#             contracts=self._cursor_contracts,
#         )


# class GlobalDataPreloader:
#     """主进程 preload：写入 RuntimeContext.global_data_meta，execute 时传给 worker。"""

#     @classmethod
#     def preload(
#         cls,
#         *,
#         settings: Dict[str, Any],
#         start_date: str,
#         end_date: str,
#         entity_ids: List[str],
#         fresh_strategy_cache: bool = False,
#     ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
#         stock_list = [str(x).strip() for x in entity_ids if str(x).strip()]
#         global_data: Dict[str, Any] = {"stock_list": stock_list}
#         loaded_slots: List[str] = ["stock_list"]

#         data_config = StrategyDataConfig(settings)
#         required = data_config.required
#         if not required:
#             return global_data, cls._meta(loaded_slots, skipped=[])

#         if fresh_strategy_cache:
#             DataContracts.shared_cache().enter_strategy_run()

#         dcm = DataContracts()
#         skipped: List[str] = []

#         for index, raw in enumerate(required):
#             item = data_config.normalize_required_item(raw, label=f"data.required[{index}]")
#             dk = DataKey(str(item["data_key"]))
#             spec = dcm.map.get(dk)
#             if spec is None:
#                 skipped.append(dk.value)
#                 logger.warning("global preload 跳过未注册 data_key: %s", dk.value)
#                 continue
#             if spec.get("scope") != ContractScope.GLOBAL:
#                 continue

#             params = dict(item.get("params") or {})
#             try:
#                 contract = dcm.issue(
#                     dk,
#                     start=start_date,
#                     end=end_date,
#                     **params,
#                 ).require_contract()
#                 slot = StrategyDataConfig.storage_key_for(dk, is_base=False)
#                 global_data[slot] = list(contract.data or [])
#                 loaded_slots.append(slot)
#             except Exception as exc:
#                 skipped.append(dk.value)
#                 logger.error("global preload 失败: data_key=%s error=%s", dk.value, exc)

#         return global_data, cls._meta(loaded_slots, skipped=skipped)

#     @staticmethod
#     def _meta(loaded_slots: List[str], *, skipped: List[str]) -> Dict[str, Any]:
#         return {
#             "loaded_slots": list(loaded_slots),
#             "skipped_data_keys": list(skipped),
#         }


# __all__ = ["EntityContractBatch", "EntityDataLoader", "GlobalDataPreloader"]
