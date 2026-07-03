# """entity_based execute_fn 入参契约（BacktestEngine JobContext → 单股执行）。"""
# from __future__ import annotations

# from dataclasses import dataclass, field
# from typing import Any, Dict, List, Mapping

# _REQUIRED_FIELDS = (
#     "entity_id",
#     "strategy_name",
#     "settings",
#     "start_date",
#     "end_date",
#     "output_dir",
#     "global_data",
#     "open_dates",
#     "backtest_calendar",
#     "worker_module_path",
#     "worker_class_name",
# )


# @dataclass(frozen=True)
# class EntityBasedExecutePayload:
#     """BacktestEngine execute_fn 在子进程内执行的单股 payload。"""

#     entity_id: str
#     strategy_name: str
#     settings: Dict[str, Any]
#     start_date: str
#     end_date: str
#     output_dir: str
#     global_data: Dict[str, Any]
#     open_dates: List[str]
#     backtest_calendar: Dict[str, Any]
#     worker_module_path: str
#     worker_class_name: str
#     job_id: str = ""
#     worker_file_path: str = ""
#     enumeration_execution_mode: str = ""
#     extras: Dict[str, Any] = field(default_factory=dict)

#     @classmethod
#     def from_mapping(cls, raw: Mapping[str, Any]) -> EntityBasedExecutePayload:
#         missing = [name for name in _REQUIRED_FIELDS if name not in raw]
#         if missing:
#             raise ValueError(
#                 f"entity_based execute payload 缺少字段: {', '.join(missing)}"
#             )

#         settings = raw["settings"]
#         if not isinstance(settings, dict):
#             raise ValueError("entity_based execute payload.settings 须为 dict")

#         global_data = raw["global_data"]
#         if not isinstance(global_data, dict):
#             raise ValueError("entity_based execute payload.global_data 须为 dict")

#         stock_list = global_data.get("stock_list")
#         if not isinstance(stock_list, list) or not stock_list:
#             raise ValueError(
#                 "entity_based execute payload.global_data.stock_list 须为非空 list"
#             )

#         entity_id = str(raw["entity_id"]).strip()
#         if not entity_id:
#             raise ValueError("entity_based execute payload.entity_id 不能为空")

#         universe = {str(x).strip() for x in stock_list if str(x).strip()}
#         if entity_id not in universe:
#             raise ValueError(
#                 f"entity_id {entity_id!r} 不在 global_data.stock_list 中"
#             )

#         open_dates_raw = raw.get("open_dates")
#         if not isinstance(open_dates_raw, list) or not open_dates_raw:
#             raise ValueError("entity_based execute payload.open_dates 须为非空 list")
#         open_dates = [str(d).strip() for d in open_dates_raw if str(d).strip()]
#         if not open_dates:
#             raise ValueError("entity_based execute payload.open_dates 无有效条目")

#         calendar = raw.get("backtest_calendar")
#         if not isinstance(calendar, dict):
#             raise ValueError("entity_based execute payload.backtest_calendar 须为 dict")
#         cal_open = calendar.get("open_dates")
#         if not isinstance(cal_open, list) or not cal_open:
#             raise ValueError("backtest_calendar.open_dates 须为非空 list")

#         extras = {
#             key: value
#             for key, value in raw.items()
#             if str(key).startswith("_")
#         }

#         return cls(
#             entity_id=entity_id,
#             strategy_name=str(raw["strategy_name"]),
#             settings=dict(settings),
#             start_date=str(raw["start_date"]),
#             end_date=str(raw["end_date"]),
#             output_dir=str(raw["output_dir"]),
#             global_data=dict(global_data),
#             open_dates=open_dates,
#             backtest_calendar=dict(calendar),
#             worker_module_path=str(raw["worker_module_path"]),
#             worker_class_name=str(raw["worker_class_name"]),
#             job_id=str(raw.get("job_id") or entity_id),
#             worker_file_path=str(raw.get("worker_file_path") or ""),
#             enumeration_execution_mode=str(raw.get("enumeration_execution_mode") or ""),
#             extras=extras,
#         )

#     def to_mapping(self) -> Dict[str, Any]:
#         """供 StrategyHookRuntime 等需要完整 job dict 的组件使用。"""
#         out: Dict[str, Any] = {
#             "entity_id": self.entity_id,
#             "stock_id": self.entity_id,
#             "job_id": self.job_id,
#             "strategy_name": self.strategy_name,
#             "settings": dict(self.settings),
#             "start_date": self.start_date,
#             "end_date": self.end_date,
#             "output_dir": self.output_dir,
#             "global_data": self.global_data,
#             "open_dates": list(self.open_dates),
#             "backtest_calendar": dict(self.backtest_calendar),
#             "worker_module_path": self.worker_module_path,
#             "worker_class_name": self.worker_class_name,
#             "worker_file_path": self.worker_file_path,
#             "enumeration_execution_mode": self.enumeration_execution_mode,
#         }
#         out.update(self.extras)
#         return out


# __all__ = ["EntityBasedExecutePayload"]
