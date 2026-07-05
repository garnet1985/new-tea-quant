"""DataKey 基类定义（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Type, Optional, List, Sequence, Mapping

from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


class ContractType:
    """Contract type enum."""
    TIME_SERIES = "time_series"
    NON_TIME_SERIES = "non_time_series"


class ContractScope:
    """Contract scope enum."""
    GLOBAL = "global"
    PER_ENTITY = "per_entity"


@dataclass
class ContractMeta:
    """Contract metadata（静态信息）。"""
    data_key: str  # 唯一标识符（如 'stock.kline.daily')
    type: str  # 'time_series' or 'non_time_series'
    scope: str  # 'global' or 'per_entity'
    display_name: str = ""  # 显示名称
    description: str = ""  # 描述
    unique_keys: List[str] = field(default_factory=list)  # 唯一键字段列表（如 ['date', 'stock_id'])
    loader: Optional[Type[BaseDataKeyLoader]] = None  # Loader 类（通过发现机制加载）

    @classmethod
    def from_dict(cls, meta: Dict[str, Any]) -> ContractMeta:
        """从字典创建 ContractMeta 实例。"""
        return cls(
            data_key=meta.get("data_key", ""),
            type=meta.get("type", ContractType.TIME_SERIES),
            scope=meta.get("scope", ContractScope.PER_ENTITY),
            display_name=meta.get("display_name", ""),
            description=meta.get("description", ""),
            unique_keys=meta.get("unique_keys", []),
            loader=meta.get("loader"),
        )


@dataclass
class ContractRuntime:
    """Contract runtime metadata（动态信息）。"""
    # 基础 runtime 字段
    start_time: Optional[str] = None  # 起始时间
    end_time: Optional[str] = None  # 结束时间
    entity_ids: Optional[List[str]] = None  # Entity IDs

    # 可选字段（根据 type/scope 不同）
    base_time_field: Optional[str] = None  # 数据中时间字段名（如 "date"）
    time_format: Optional[str] = None  # 时间格式（如 "YYYYMMDD")
    is_cached: bool = False  # 是否缓存（仅 global scope）

    @classmethod
    def from_dict(cls, runtime: Dict[str, Any]) -> ContractRuntime:
        """从字典创建 ContractRuntime 实例（支持动态字段）。"""
        # 动态创建 dataclass 子类（包含额外字段）
        if not runtime:
            return cls()

        # 基础字段
        base_fields = {
            "start_time": runtime.get("start_time"),
            "end_time": runtime.get("end_time"),
            "entity_ids": runtime.get("entity_ids"),
            "base_time_field": runtime.get("base_time_field"),
            "time_format": runtime.get("time_format"),
            "is_cached": runtime.get("is_cached", False),
        }

        # 额外字段（如 adjust, amount, direction 等）
        extra_fields = {}
        known_fields = set(base_fields.keys())
        for key, value in runtime.items():
            if key not in known_fields:
                extra_fields[key] = value

        if extra_fields:
            # 动态创建包含额外字段的 dataclass
            runtime_cls = dataclass(type(
                "DynamicContractRuntime",
                (cls,),
                {key: field(default=value) for key, value in extra_fields.items()}
            ))
            return runtime_cls(**base_fields, **extra_fields)

        return cls(**base_fields)


@dataclass
class ContractSpecific:
    """Contract-specific metadata（特有字段）。"""
    # 子类定义特有字段
    # 示例（stock.kline）：
    # term: str = "daily"
    # adjust: str = "qfq"

    @classmethod
    def from_dict(cls, specific: Dict[str, Any]) -> ContractSpecific:
        """从字典创建 ContractSpecific 实例。"""
        # 动态创建子类实例（包含特定字段）
        if not specific:
            return cls()
        
        # 动态创建 dataclass 子类
        specific_cls = dataclass(type(
            "DynamicContractSpecific",
            (cls,),
            {key: field(default_factory=lambda: value) if isinstance(value, (list, dict)) else field(default=value)
             for key, value in specific.items()}
        ))
        return specific_cls(**specific)


@dataclass
class BaseDataKey:
    """DataKey 基类（meta/runtime/specific 三层结构）。"""

    meta: ContractMeta  # 静态信息
    runtime: ContractRuntime  # 动态信息
    specific: ContractSpecific  # 特有字段

    # status
    data: Optional[Any] = None  # 数据缓存（可以是 list 或 dict）
    is_loaded: bool = False  # 是否加载
    is_cached: bool = False  # 是否缓存（仅 global scope）

    def __init__(self, declaration: dict):
        """初始化 DataKey 实例。

        Args:
            declaration: 用户声明（包含 meta/specific，runtime 可选）
        """
        self.validate_declaration(declaration)
        self.meta = ContractMeta.from_dict(declaration.get("meta", {}))
        # runtime 可选（运行时注入）
        self.runtime = ContractRuntime.from_dict(declaration.get("runtime", {})) if "runtime" in declaration else ContractRuntime()
        self.specific = ContractSpecific.from_dict(declaration.get("specific", {}))

    def validate_declaration(self, declaration: dict) -> bool:
        """检查 DataKey 完整性（是否包含所有必填字段）。

        Returns:
            True 如果完整

        Raises:
            ValueError: 如果缺少必填字段
        """
        if "meta" not in declaration:
            raise ValueError("declaration 缺少 'meta' 字段")
        
        meta = declaration["meta"]
        if "data_key" not in meta:
            raise ValueError("meta 缺少 'data_key' 字段")

        # 验证 meta
        self._validate_meta(meta)

        return True

    def add_runtime(self, runtime: dict) -> 'BaseDataKey':
        """添加运行时信息（支持链式调用）。

        Args:
            runtime: 运行时信息字典

        Returns:
            self（支持链式调用）

        示例：
            contract.add_runtime({...}).fill_in_data()
        """
        self.runtime = ContractRuntime.from_dict(runtime)
        self._validate_runtime(runtime)
        return self

    def is_global(self) -> bool:
        """检查 DataKey 是否为 GLOBAL scope。"""
        return self.meta.scope == ContractScope.GLOBAL

    def is_time_series(self) -> bool:
        """检查 DataKey 是否为 TIME_SERIES 类型。"""
        return self.meta.type == ContractType.TIME_SERIES

    def _is_global_from_dict(self, meta: dict) -> bool:
        """从 meta dict 判断是否为 GLOBAL scope。"""
        return meta.get("scope") == ContractScope.GLOBAL

    def _is_time_series_from_dict(self, meta: dict) -> bool:
        """从 meta dict 判断是否为 TIME_SERIES 类型。"""
        return meta.get("type") == ContractType.TIME_SERIES

    def _validate_meta(self, meta: dict) -> None:
        """验证 ContractMeta 字段。"""
        if not meta.get("data_key"):
            raise ValueError("meta.data_key 不能为空")
        
        if meta.get("type") not in [ContractType.TIME_SERIES, ContractType.NON_TIME_SERIES]:
            raise ValueError(f"meta.type 必须是 '{ContractType.TIME_SERIES}' 或 '{ContractType.NON_TIME_SERIES}'")
        
        if meta.get("scope") not in [ContractScope.GLOBAL, ContractScope.PER_ENTITY]:
            raise ValueError(f"meta.scope 必须是 '{ContractScope.GLOBAL}' 或 '{ContractScope.PER_ENTITY}'")

    def _validate_runtime(self, runtime: dict) -> None:
        """验证 ContractRuntime 字段。"""
        # Runtime 必须包含必要信息才能加载
        # Per entity scope：必须有 entity_ids
        if self.meta.scope == ContractScope.PER_ENTITY:
            if not runtime.get("entity_ids"):
                raise ValueError(f"Per entity contract {self.meta.data_key} 的 runtime 必须包含 entity_ids")
        
        # Time series：可以验证 start_time/end_time（可选）
        # 其他 runtime 参数（adjust, amount 等）可选

    def get_entity_ids(self) -> Optional[List[str]]:
        """获取所有实体 ID。"""
        return self.runtime.entity_ids

    def get_entity_data(self, entity_id: str) -> Optional[Any]:
        """根据实体 ID 获取实体数据。

        Args:
            entity_id: Entity ID

        Returns:
            Entity 数据（如果是 per_entity scope 且 data 是 dict）
            或全部数据（如果是 global scope）
        """
        if self.is_global():
            # Global scope：返回相同数据
            return self.data
        
        # Per entity scope：从 dict 中获取
        if isinstance(self.data, dict):
            return self.data.get(entity_id)
        
        return None

    def get_entities_data(self) -> Optional[Mapping[str, Any]]:
        """获取所有实体数据。

        Returns:
            Dict[entity_id, data]（如果是 per_entity scope）
            或全部数据（如果是 global scope）
        """
        if self.is_global():
            # Global scope：返回相同数据
            if self.data is None:
                return None
            # 返回 dict（每个 entity_id 映射到相同数据）
            entity_ids = self.runtime.entity_ids or []
            return {entity_id: self.data for entity_id in entity_ids}
        
        # Per entity scope：返回 dict
        if isinstance(self.data, dict):
            return self.data
        
        return None

    def fill_in_data(self, runtime: Optional[dict] = None, force_reload: bool = False) -> None:
        """自动填充数据（根据 entity 数量选择加载方式）。

        Args:
            runtime: 运行时信息（可选，如果提供则自动注入）
            force_reload: 是否强制重新加载

        前提：
        - 必须有 runtime 信息（通过 add_runtime、declaration 或 runtime 参数提供）

        逻辑：
        - Global scope：调用 loader.load()
        - Per entity scope：
          - 单个 entity：调用 loader.load()
          - 多个 entity：调用 loader.load_batch()
        - 将数据存入 self.data，设置 is_loaded = True

        示例：
            # 方式1：链式调用
            contract.add_runtime({...}).fill_in_data()

            # 方式2：直接传参数
            contract.fill_in_data(runtime={...})
        """
        # 如果提供了 runtime 参数，先注入
        if runtime is not None:
            self.add_runtime(runtime)

        if self.is_loaded and not force_reload:
            # 已加载，跳过
            return

        # 检查 runtime 信息
        if self.meta.loader is None:
            raise ValueError(f"Contract {self.meta.data_key} 没有定义 loader")

        # Per entity scope：必须有 entity_ids
        if not self.is_global():
            entity_ids = self.get_entity_ids()
            if not entity_ids:
                raise ValueError(f"Per entity contract {self.meta.data_key} 需要 runtime.entity_ids（请调用 add_runtime 或提供 runtime 参数）")

        # 构建 params（从 specific + runtime）
        params = self._build_params()

        # 根据 scope 和 entity_ids 决定调用方式
        if self.is_global():
            # Global scope：调用 loader.load()
            self.data = self.meta.loader().load(params)
        else:
            # Per entity scope：根据 entity_ids 数量决定
            entity_ids = self.get_entity_ids()

            if len(entity_ids) == 1:
                # 单个 entity：调用 loader.load()
                params["entity_id"] = entity_ids[0]
                self.data = self.meta.loader().load(params)
            else:
                # 多个 entity：调用 loader.load_batch()
                self.data = self.meta.loader().load_batch(entity_ids, params)

        # 标记已加载
        self.is_loaded = True

    def _build_params(self) -> Dict[str, Any]:
        """构建 Loader params（从 specific + runtime）。

        Returns:
            Params 字典
        """
        params = {}

        # Specific 字段（动态获取）
        for key, value in self.specific.__dict__.items():
            if not key.startswith("_"):
                params[key] = value

        # Runtime 基础字段（映射 loader 参数）
        if self.runtime.start_time is not None:
            params["start"] = self.runtime.start_time
        if self.runtime.end_time is not None:
            params["end"] = self.runtime.end_time

        # Runtime 动态字段（如 adjust, amount, direction 等）
        # 获取所有 runtime 字段，排除基础字段
        base_runtime_fields = {
            "start_time", "end_time", "entity_ids",
            "base_time_field", "time_format", "is_cached"
        }
        for key, value in self.runtime.__dict__.items():
            if not key.startswith("_") and key not in base_runtime_fields:
                # 动态字段直接传递给 loader
                params[key] = value

        return params


    # def load(self) -> Any:
    #     """加载单个数据（不需要 params）。

    #     Returns:
    #         加载的数据
    #     """
    #     if self.meta.loader is None:
    #         raise ValueError(f"Contract {self.meta.data_key} 没有定义 loader")

    #     # 构建 params（从 specific + runtime）
    #     params = self._build_params()

    #     # 根据 scope 调用不同的 loader 方法
    #     if self.is_global():
    #         # Global scope：不需要 entity_id
    #         return self.meta.loader().load(params)
    #     else:
    #         # Per entity scope：需要 entity_id
    #         entity_ids = self.get_entity_ids()
    #         if not entity_ids or len(entity_ids) != 1:
    #             raise ValueError(f"Per entity contract {self.meta.data_key} 需要 entity_ids 且长度为 1")
    #         params["entity_id"] = entity_ids[0]
    #         return self.meta.loader().load(params)

    # def load_batch(self) -> Mapping[str, Any]:
    #     """批量加载多个 entity 数据（不需要 params）。

    #     Returns:
    #         Dict[entity_id, data]: 每个 entity 对应的数据
    #     """
    #     if self.meta.loader is None:
    #         raise ValueError(f"Contract {self.meta.data_key} 没有定义 loader")

    #     entity_ids = self.get_entity_ids()
    #     if not entity_ids:
    #         raise ValueError(f"Contract {self.meta.data_key} 需要 entity_ids")

    #     # 构建 params（从 specific + runtime）
    #     params = self._build_params()

    #     # 根据 scope 调用不同的 loader 方法
    #     if self.is_global():
    #         # Global scope：返回相同数据
    #         data = self.meta.loader().load(params)
    #         return {entity_id: data for entity_id in entity_ids}
    #     else:
    #         # Per entity scope：批量加载
    #         return self.meta.loader().load_batch(entity_ids, params)

    # def _build_params(self) -> Dict[str, Any]:
    #     """构建 Loader params（从 specific + runtime）。

    #     Returns:
    #         Params 字典
    #     """
    #     params = {}

    #     # Specific 字段（动态获取）
    #     for key, value in self.specific.__dict__.items():
    #         if not key.startswith("_"):
    #             params[key] = value

    #     # Runtime 字段（映射 loader 参数）
    #     if self.runtime.start_time is not None:
    #         params["start"] = self.runtime.start_time
    #     if self.runtime.end_time is not None:
    #         params["end"] = self.runtime.end_time

    #     return params


__all__ = ['BaseDataKey', 'ContractType', 'ContractScope', 'ContractMeta', 'ContractRuntime', 'ContractSpecific']