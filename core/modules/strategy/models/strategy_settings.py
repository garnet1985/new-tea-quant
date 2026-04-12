#!/usr/bin/env python3
"""
Strategy Settings - 策略配置模型

职责：
- 表示策略配置（直接使用字典，灵活支持用户自定义结构）
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.data_contract.contract_const import DataKey


class StrategySettings:
    """
    策略配置（基于字典的灵活配置）

    **主数据依赖** ``data.base_required_data``（仅支持 K 线主源）：

    - 只使用 ``DataKey.STOCK_KLINE``（``stock.kline``）。不在此写 ``stock.kline.daily.qfq`` 等细粒度 key，
      周期与复权一律由 ``params`` 表达。
    - ``data_id`` **可省略**；若填写则**只能**为 ``stock.kline``。
    - **必须**提供 ``params``，且其中 **``term`` 必填**（如 ``daily`` / ``weekly`` / ``monthly``）。
    - ``adjust`` 可选，**默认 ``qfq``**；其它键（如 ``tag_storage_entity_type``）可一并放在 ``params`` 里。

    **额外依赖** ``data.extra_required_data_sources``：每条须带 ``data_id``（如 ``tag``、``macro.gdp`` 等）。
    若某条也是 ``stock.kline``，则同样要求 ``params.term``，``adjust`` 默认 ``qfq``。
    策略配置中**不允许**使用 ``stock.kline.daily.qfq`` 等细粒度 K 线 DataKey（请改用 ``stock.kline`` + ``params``）。
    """

    def __init__(self, settings_dict: Dict[str, Any]):
        self._settings = settings_dict

        self.name = settings_dict.get("name", "unknown")
        self.description = settings_dict.get("description", "")
        self.is_enabled = settings_dict.get("is_enabled", False)

        self.core = settings_dict.get("core", {})
        self.data = settings_dict.get("data", {})
        self.sampling = settings_dict.get("sampling", {})
        self.price_simulator = settings_dict.get("price_simulator", {})
        self.goal = settings_dict.get("goal", {})
        self.performance = settings_dict.get("performance", {})

    @staticmethod
    def normalize_base_required_data(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        主依赖：仅 ``stock.kline``；``data_id`` 可省略；``params.term`` 必填；``adjust`` 默认 qfq。
        """
        if not isinstance(raw, dict):
            raise ValueError("data.base_required_data 必须为 dict")
        params = raw.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValueError("data.base_required_data.params 必须为 dict")

        raw_id = raw.get("data_id")
        if raw_id is None or (isinstance(raw_id, str) and not raw_id.strip()):
            data_id = DataKey.STOCK_KLINE.value
        else:
            data_id = str(raw_id).strip()
            if data_id != DataKey.STOCK_KLINE.value:
                raise ValueError(
                    f"data.base_required_data.data_id 只能为 {DataKey.STOCK_KLINE.value!r} 或省略；"
                    f"勿使用细粒度 K 线 key，请用 params.term / params.adjust 声明周期与复权"
                )

        term = params.get("term")
        if term is None or (isinstance(term, str) and not term.strip()):
            raise ValueError(
                "data.base_required_data.params 必须提供非空的 term（如 daily / weekly / monthly）"
            )

        merged = dict(params)
        if "adjust" not in merged or (
            isinstance(merged.get("adjust"), str) and not str(merged.get("adjust")).strip()
        ):
            merged["adjust"] = "qfq"

        return {"data_id": data_id, "params": merged}

    @staticmethod
    def normalize_extra_required_data_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """额外数据源：须含 data_id；``stock.kline`` 时与主依赖相同的 params 规则；禁止细粒度 K 线 key。"""
        if not isinstance(item, dict):
            raise ValueError("数据源项必须为 dict")
        raw_id = item.get("data_id")
        if not raw_id or not str(raw_id).strip():
            raise ValueError("extra_required_data_sources 每项必须包含非空的 data_id")
        data_id = str(raw_id).strip()

        if data_id in (DataKey.STOCK_KLINE_DAILY_QFQ.value, DataKey.STOCK_KLINE_DAILY_NFQ.value):
            raise ValueError(
                f"策略配置不支持 data_id={data_id!r}，请改用 {DataKey.STOCK_KLINE.value!r} "
                "并在 params 中指定 term、adjust（adjust 可省略，默认 qfq）"
            )

        params = item.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValueError("数据源 params 必须为 dict")

        if data_id == DataKey.STOCK_KLINE.value:
            term = params.get("term")
            if term is None or (isinstance(term, str) and not term.strip()):
                raise ValueError(
                    f"data_id 为 {DataKey.STOCK_KLINE.value} 时 params 必须提供非空的 term"
                )
            merged = dict(params)
            if "adjust" not in merged or (
                isinstance(merged.get("adjust"), str) and not str(merged.get("adjust")).strip()
            ):
                merged["adjust"] = "qfq"
            return {"data_id": data_id, "params": merged}

        return {"data_id": data_id, "params": dict(params)}

    @staticmethod
    def validate_data_config(data: Dict[str, Any]) -> None:
        """校验 ``data`` 中与数据契约相关的字段（fail-fast）。"""
        base = data.get("base_required_data")
        if not isinstance(base, dict):
            raise ValueError("data.base_required_data 必须为 dict")
        StrategySettings.normalize_base_required_data(base)

        extra = data.get("extra_required_data_sources", [])
        if extra is None:
            return
        if not isinstance(extra, list):
            raise ValueError("data.extra_required_data_sources 必须为 list")
        for i, item in enumerate(extra):
            if not isinstance(item, dict):
                raise ValueError(f"data.extra_required_data_sources[{i}] 必须为 dict")
            try:
                StrategySettings.normalize_extra_required_data_item(item)
            except ValueError as e:
                raise ValueError(f"data.extra_required_data_sources[{i}]: {e}") from e

    @property
    def base_required_data(self) -> Dict[str, Any]:
        b = self.data.get("base_required_data")
        if not isinstance(b, dict):
            raise ValueError("缺少 data.base_required_data")
        return b

    @property
    def extra_required_data_sources(self) -> List[Dict[str, Any]]:
        xs = self.data.get("extra_required_data_sources", [])
        if xs is None:
            return []
        if not isinstance(xs, list):
            return []
        return list(xs)

    @property
    def required_data_sources(self) -> List[Dict[str, Any]]:
        """规范化后的主依赖 + 额外依赖列表（用于按序加载）。"""
        base = self.normalize_base_required_data(self.base_required_data)
        rest = [self.normalize_extra_required_data_item(x) for x in self.extra_required_data_sources]
        return [base] + rest

    @property
    def resolved_base_required_data(self) -> Dict[str, Any]:
        """规范化后的主依赖（签发/加载使用）。"""
        return self.normalize_base_required_data(self.base_required_data)

    @property
    def min_required_records(self) -> int:
        return int(self.data.get("min_required_records", 100) or 100)

    @property
    def adjust_type(self) -> str:
        p = self.resolved_base_required_data.get("params") or {}
        return str(p.get("adjust", "qfq"))

    @property
    def indicators(self) -> Dict[str, Any]:
        return self.data.get("indicators", {}) or {}

    @property
    def tag_storage_entity_type(self) -> str:
        """写入 ``sys_tag_value.entity_type`` 时与历史行为对齐的默认类型。"""
        p = self.resolved_base_required_data.get("params") or {}
        return str(p.get("tag_storage_entity_type", "stock_kline_daily"))

    @property
    def start_date(self) -> str:
        return self.price_simulator.get("start_date", "") or ""

    @property
    def end_date(self) -> str:
        return self.price_simulator.get("end_date", "") or ""

    @property
    def sampling_amount(self) -> int:
        return int(self.sampling.get("sampling_amount", 10) or 10)

    @property
    def sampling_config(self) -> Dict[str, Any]:
        return self.sampling

    @property
    def max_workers(self) -> Any:
        simulator_cfg = self.price_simulator or {}
        enumerator_cfg = self.get("enumerator") or {}
        performance_cfg = self.performance or {}
        return (
            simulator_cfg.get("max_workers")
            or enumerator_cfg.get("max_workers")
            or performance_cfg.get("max_workers")
            or "auto"
        )

    def to_dict(self) -> Dict[str, Any]:
        return self._settings

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategySettings":
        return cls(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)
