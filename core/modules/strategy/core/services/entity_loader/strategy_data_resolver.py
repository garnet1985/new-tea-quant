"""settings.data 声明解析与 global / per_entity 分组。

消费者: scanner, enumerator
（整块消费者见 entity_loader/__init__.py）

本文件:
- StrategyDataResolver: base/required 声明、ContractIssuer.is_global 分组
- DataDeclaration / DeclarationGroups: 声明与分组 TypedDict
  边界: 负责解析与分组；不负责实际 contract 加载（GlobalEntityCache / JobBundleLoader）

同进程优先传 ``StrategySettings``（读 ``raw_settings``，避免再 ``to_dict``）。
跨进程 job payload 仍应序列化为 dict；worker 侧 ``from_dict`` 后再传入本类。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, TypedDict, Union

from core.modules.data_contract import DATA_KEY, ContractIssuer
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

logger = logging.getLogger(__name__)

# 系统级 global 数据：由 GlobalEntityCache 固定加载，不参与 settings.data 分组
SYSTEM_GLOBAL_DATA_KEYS = frozenset({
    DATA_KEY.STOCK_LIST,
    DATA_KEY.TRADE_CALENDAR,
})

# 回测默认自动注入的 per_entity 旁路数据（用户 settings.data 无需声明）
SYSTEM_AUTO_REQUIRED_DATA_KEYS = (
    DATA_KEY.STOCK_ST_PERIODS,
)

SettingsInput = Union[StrategySettings, Mapping[str, Any]]


class DataDeclaration(TypedDict):
    """数据声明结构。"""
    data_key: str
    params: Dict[str, Any]
    indicators: Dict[str, Any]
    scope: str  # 'global' or 'per_entity'


class DeclarationGroups(TypedDict):
    """分组的数据声明。"""
    global_declarations: List[DataDeclaration]
    per_entity_declarations: List[DataDeclaration]


class StrategyDataResolver:
    """从 settings.data 解析声明并按 scope 分组。

    职责：
    1. 解析 base + required 数据声明
    2. 回测默认注入系统旁路数据（如 ``stock.st_periods``）
    3. 用 ContractIssuer.is_global() 分组为 global / per_entity
    4. 供 GlobalEntityCache（加载 global）与 JobBuilder（构建 per_entity job）消费

    不负责：
    - 系统级 global（stock.list、trade.calendar、latest completed trading date）
      → GlobalEntityCache.init_system_globals()
    - 实际加载 contract 数据 → GlobalEntityCache / JobBundleLoader
    """

    def __init__(self, settings: SettingsInput) -> None:
        self._settings = self._coerce_mapping(settings)
        data = self._settings.get("data")
        if not isinstance(data, dict):
            raise ValueError("settings.data 必填且须为 dict")
        self._data = data

        base = self._data.get("base")
        if not isinstance(base, dict):
            raise ValueError("data.base 必填且须为 dict")

        raw_required = self._data.get("required")
        if raw_required is not None and not isinstance(raw_required, list):
            raise ValueError("data.required 须为 list")

    @staticmethod
    def _coerce_mapping(settings: SettingsInput) -> Mapping[str, Any]:
        """同进程 ``StrategySettings`` → 直接用 ``raw_settings``（不深拷）。"""
        if isinstance(settings, StrategySettings):
            return settings.raw_settings
        return dict(settings or {})

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

    def issue_declarations(self) -> List[Dict[str, Any]]:
        """base + required + 系统默认旁路，供 issue 迭代（不写入 settings）。"""
        items = [self._normalize_declaration(self.base)]
        seen = {str(items[0]["data_key"])}
        for index, raw in enumerate(self.required):
            if not isinstance(raw, dict):
                raise ValueError(f"data.required[{index}] 须为 dict")
            item = self._normalize_declaration(raw, label=f"data.required[{index}]")
            data_key = str(item["data_key"])
            if data_key in seen:
                raise ValueError(f"data 声明重复 data_key: {data_key!r}")
            seen.add(data_key)
            items.append(item)
        for auto_key in SYSTEM_AUTO_REQUIRED_DATA_KEYS:
            key = str(auto_key)
            if key in seen:
                continue
            if not self._should_auto_inject(key):
                continue
            items.append(
                {
                    "data_key": key,
                    "params": {},
                    "indicators": {},
                }
            )
            seen.add(key)
            logger.debug("auto-inject data declaration: %s", key)
        return items

    def _should_auto_inject(self, data_key: str) -> bool:
        """是否默认注入旁路 contract。

        ``stock.st_periods``：base 为股票 K 线族时注入（A 股回测主路径）。
        """
        if data_key == DATA_KEY.STOCK_ST_PERIODS:
            base_key = str(self.base.get("data_key") or "").strip()
            return base_key.startswith("stock.kline.")
        return False

    @staticmethod
    def normalize_indicators(raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("indicators 必须为 dict")
        return dict(raw)

    def _normalize_declaration(
        self,
        raw: Dict[str, Any],
        *,
        label: str = "data declaration",
    ) -> Dict[str, Any]:
        raw_key = raw.get("data_key")
        if not raw_key or not str(raw_key).strip():
            raise ValueError(f"{label}.data_key 必填")
        data_key = str(raw_key).strip()

        params = raw.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValueError(f"{label}.params 必须为 dict")

        return {
            "data_key": data_key,
            "params": dict(params),
            "indicators": self.normalize_indicators(raw.get("indicators")),
        }

    @staticmethod
    def storage_key_for(data_key: str, *, is_base: bool = False) -> str:
        """Hook / loader 数据槽位名（与 data_key 字符串一致）。"""
        _ = is_base
        return data_key

    @classmethod
    def group_from_settings(cls, settings: SettingsInput) -> DeclarationGroups:
        """从 settings 分组声明；无 data 或解析失败时返回空分组。"""
        mapping = cls._coerce_mapping(settings)
        data = mapping.get("data")
        if not isinstance(data, dict):
            return {"global_declarations": [], "per_entity_declarations": []}
        try:
            return cls(settings).group_declarations()
        except ValueError as exc:
            logger.warning("声明分组失败：%s", exc)
            return {"global_declarations": [], "per_entity_declarations": []}

    def group_declarations(self) -> DeclarationGroups:
        """将 settings.data 声明按 ContractIssuer.is_global() 分组。"""
        global_declarations: List[DataDeclaration] = []
        per_entity_declarations: List[DataDeclaration] = []

        issuer = ContractIssuer()
        issuer.discover()
        available_keys = set(issuer.list_available_keys())

        for declaration in self.issue_declarations():
            data_key_str = declaration["data_key"]

            if data_key_str in SYSTEM_GLOBAL_DATA_KEYS:
                logger.debug("跳过系统 global 数据声明: %s", data_key_str)
                continue

            if data_key_str not in available_keys:
                logger.warning("未注册的 data_key: %s，跳过分组", data_key_str)
                continue

            scope = "global" if ContractIssuer.is_global(data_key_str) else "per_entity"
            full_declaration: DataDeclaration = {
                "data_key": data_key_str,
                "params": declaration["params"],
                "indicators": declaration["indicators"],
                "scope": scope,
            }

            if scope == "global":
                global_declarations.append(full_declaration)
            else:
                per_entity_declarations.append(full_declaration)

        logger.debug(
            "group_declarations() 完成：%d global，%d per_entity",
            len(global_declarations),
            len(per_entity_declarations),
        )

        return {
            "global_declarations": global_declarations,
            "per_entity_declarations": per_entity_declarations,
        }


__all__ = [
    "StrategyDataResolver",
    "DataDeclaration",
    "DeclarationGroups",
    "SYSTEM_GLOBAL_DATA_KEYS",
    "SettingsInput",
]
