"""settings.data 声明解析（contract 注入边界）。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.data_contract.contracts import DataKey
from core.modules.data_contract.core.registry.kline_keys import (
    PRIMARY_KLINE_SLOT,
    STOCK_KLINE_DATA_ID_VALUES,
    is_stock_kline_data_key,
    kline_term_from_data_id_value,
)


class StrategyDataConfig:
    """从 settings.data 解析 base（时间轴）+ required（附加依赖）。"""

    _STORAGE_KEY_ALIASES = {
        DataKey.TAG: "tags",
    }

    def __init__(self, settings: Dict[str, Any]) -> None:
        self._settings = dict(settings or {})
        data = self._settings.get("data")
        if not isinstance(data, dict):
            raise ValueError("settings.data 必填且须为 dict")
        self._data = data

        base = self._data.get("base")
        if not isinstance(base, dict):
            raise ValueError("data.base 必填且须为 dict")
        self.normalize_base(base)

        raw_required = self._data.get("required")
        if raw_required is not None and not isinstance(raw_required, list):
            raise ValueError("data.required 须为 list")

    @property
    def data(self) -> Dict[str, Any]:
        return dict(self._data)

    @property
    def base(self) -> Dict[str, Any]:
        base = self._data.get("base")
        if not isinstance(base, dict):
            raise ValueError("data.base 必填且须为 dict")
        return dict(base)

    @property
    def required(self) -> List[Dict[str, Any]]:
        raw = self._data.get("required")
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ValueError("data.required 须为 list")
        return list(raw)

    @property
    def min_required_records(self) -> int:
        if "min_required_records" in self._data:
            return max(1, int(self._data["min_required_records"]))
        core = self._settings.get("core")
        if isinstance(core, dict) and "min_required_records" in core:
            return max(1, int(core["min_required_records"]))
        return 20

    @property
    def tag_storage_entity_type(self) -> str:
        base = self.normalize_base(self.base)
        params = dict(base.get("params") or {})
        explicit = str(params.get("tag_storage_entity_type") or "").strip()
        if explicit:
            return explicit
        data_key = str(base.get("data_key") or "").strip()
        if data_key in STOCK_KLINE_DATA_ID_VALUES:
            return f"stock_kline_{kline_term_from_data_id_value(data_key)}"
        return "stock_kline_daily"

    def issue_declarations(self) -> List[Dict[str, Any]]:
        """base + required，供 DCM issue 迭代（不写入 settings）。"""
        items = [self.normalize_base(self.base)]
        seen = {str(items[0]["data_key"])}
        for index, raw in enumerate(self.required):
            if not isinstance(raw, dict):
                raise ValueError(f"data.required[{index}] 须为 dict")
            item = self.normalize_required_item(raw, label=f"data.required[{index}]")
            data_key = str(item["data_key"])
            if data_key in seen:
                raise ValueError(f"data 声明重复 data_key: {data_key!r}")
            seen.add(data_key)
            items.append(item)
        return items

    @staticmethod
    def normalize_indicators(raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("indicators 必须为 dict")
        return dict(raw)

    @classmethod
    def normalize_base(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        params = raw.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValueError("data.base.params 必须为 dict")

        raw_key = raw.get("data_key")
        if raw_key is None or (isinstance(raw_key, str) and not str(raw_key).strip()):
            raise ValueError("data.base.data_key 必填")
        data_key = str(raw_key).strip()
        if data_key not in STOCK_KLINE_DATA_ID_VALUES:
            raise ValueError(
                "data.base.data_key 须为 stock.kline.daily/weekly/monthly；"
                f"收到 {data_key!r}"
            )

        merged = dict(params)
        merged.setdefault("adjust", "qfq")
        return {
            "data_key": data_key,
            "params": merged,
            "indicators": cls.normalize_indicators(raw.get("indicators")),
        }

    @classmethod
    def normalize_required_item(
        cls,
        item: Dict[str, Any],
        *,
        label: str = "data.required[]",
    ) -> Dict[str, Any]:
        raw_key = item.get("data_key")
        if not raw_key or not str(raw_key).strip():
            raise ValueError(f"{label}.data_key 必填")
        data_key = str(raw_key).strip()

        params = item.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValueError(f"{label}.params 必须为 dict")

        if data_key in STOCK_KLINE_DATA_ID_VALUES:
            merged = dict(params)
            merged.setdefault("adjust", "qfq")
            return {
                "data_key": data_key,
                "params": merged,
                "indicators": cls.normalize_indicators(item.get("indicators")),
            }
        return {
            "data_key": data_key,
            "params": dict(params),
            "indicators": cls.normalize_indicators(item.get("indicators")),
        }

    def normalize_declaration_item(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(raw)
        dk = DataKey(str(item["data_key"]))
        params = dict(item.get("params") or {})
        if dk == DataKey.TAG and str(params.get("entity_type") or "").strip() == "":
            params["entity_type"] = self.tag_storage_entity_type
            item["params"] = params
        return item

    @staticmethod
    def storage_key_for(data_key: DataKey, *, is_base: bool = False) -> str:
        """base K 线 → ``klines``；其余默认为 data_key 字符串。"""
        if is_base and is_stock_kline_data_key(data_key):
            return PRIMARY_KLINE_SLOT
        return StrategyDataConfig._STORAGE_KEY_ALIASES.get(data_key, data_key.value)


__all__ = ["StrategyDataConfig"]
