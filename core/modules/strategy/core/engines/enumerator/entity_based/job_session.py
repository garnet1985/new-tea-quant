# """entity_based 子进程数据会话（init 产出，execute 消费）。"""
# from __future__ import annotations

# from dataclasses import dataclass, field
# from typing import Any, Dict, List

# from core.modules.strategy.core.services.data.entity_data import (
#     EntityContractBatch,
#     EntityDataLoader,
# )


# @dataclass
# class EntityBasedJobSession:
#     entity_ids: List[str]
#     settings: Dict[str, Any]
#     global_data: Dict[str, Any]
#     actual_start: str
#     end_date: str
#     contract_batch: EntityContractBatch
#     _loaders: Dict[str, EntityDataLoader] = field(default_factory=dict)

#     def loader_for(self, entity_id: str) -> EntityDataLoader:
#         eid = str(entity_id).strip()
#         loader = self._loaders.get(eid)
#         if loader is None:
#             raise ValueError(f"entity_id {eid!r} 不在当前 job 批量装载范围内")
#         return loader

#     def release(self) -> None:
#         for loader in self._loaders.values():
#             loader.clear_working_state()
#         self._loaders.clear()


# __all__ = ["EntityBasedJobSession"]
