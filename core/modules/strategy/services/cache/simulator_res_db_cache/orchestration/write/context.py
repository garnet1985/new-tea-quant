"""一次 ``write_cache`` 的中间态，供 write 链路各 step 传递（避免长参数列表）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WriteCacheContext:
    """编排层内部使用；字段随实现迭代增减。"""

    strategy_name: str = ""
    simulator_name: str = ""
    raw_settings: Dict[str, Any] = field(default_factory=dict)
    normalized_settings_dict: Dict[str, Any] = field(default_factory=dict)
    stock_ids: List[str] = field(default_factory=list)
    env_start_date: str = ""
    env_end_date: str = ""
    run_mode: str = ""
    engine_version: str = ""
    worker_module_path: str = ""
    worker_class_name: str = ""
    worker_code_hash: str = ""
    data_contract_mapping: str = ""
