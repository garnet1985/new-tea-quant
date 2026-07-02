"""settings.data 声明解析（contract 注入边界）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, TypedDict

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey, ContractScope

logger = logging.getLogger(__name__)


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
    """从 settings.data 解析 base（时间轴）+ required（附加依赖）。

    职责：
    1. 解析 settings.data，获取所有数据声明（base + required）
    2. 根据 scope 分组（global 和 per_entity）
    3. 不负责验证 base 类型或推断 entity_type（由 data_contract 处理）
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        self._settings = dict(settings or {})
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
        """base + required，供 DCM issue 迭代（不写入 settings）。"""
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
        return items

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
        """规范化数据声明（不强制验证 base 类型）。"""
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
    def storage_key_for(data_key: DataKey, *, is_base: bool = False) -> str:
        """Hook / loader 数据槽位名：与 ``DataKey`` 字符串一致（无别名）。"""
        _ = is_base
        return data_key.value

    def group_declarations(self) -> DeclarationGroups:
        """解析 settings.data，将声明按 scope 分组。

        Returns:
            分组的数据声明（global_declarations 和 per_entity_declarations）

        流程：
        1. 使用 issue_declarations() 获取所有声明（base + required）
        2. 使用 DataContracts().map.get() 获取每个声明的 spec
        3. 根据 spec["scope"] 分组为 global 和 per_entity
        """
        global_declarations: List[DataDeclaration] = []
        per_entity_declarations: List[DataDeclaration] = []

        try:
            # 获取所有声明
            declarations = self.issue_declarations()

            # 创建 DataContracts 实例用于查询 spec
            dcm = DataContracts()

            for declaration in declarations:
                data_key_str = declaration["data_key"]
                data_key = DataKey(data_key_str)

                # 查询 spec
                spec = dcm.map.get(data_key)
                if spec is None:
                    logger.warning(f"未注册的 data_key: {data_key_str}，跳过")
                    continue

                # 获取 scope
                scope_str = spec.get("scope", "")
                if scope_str == ContractScope.GLOBAL:
                    scope = "global"
                elif scope_str == ContractScope.PER_ENTITY:
                    scope = "per_entity"
                else:
                    logger.warning(f"未知的 scope: {scope_str} for {data_key_str}，跳过")
                    continue

                # 构造完整的数据声明（包含 scope）
                full_declaration: DataDeclaration = {
                    "data_key": data_key_str,
                    "params": declaration["params"],
                    "indicators": declaration["indicators"],
                    "scope": scope,
                }

                # 根据 scope 分组
                if scope == "global":
                    global_declarations.append(full_declaration)
                else:
                    per_entity_declarations.append(full_declaration)

            logger.debug(
                f"group_declarations() 完成：{len(global_declarations)} global，"
                f"{len(per_entity_declarations)} per_entity"
            )

        except Exception as e:
            logger.error(f"group_declarations() 失败：{e}，返回空列表")
            global_declarations = []
            per_entity_declarations = []

        return {
            "global_declarations": global_declarations,
            "per_entity_declarations": per_entity_declarations,
        }


__all__ = ["StrategyDataResolver", "DataDeclaration", "DeclarationGroups"]
