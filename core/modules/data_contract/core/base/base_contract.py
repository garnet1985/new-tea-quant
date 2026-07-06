"""DataContract 基类定义（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Type, Optional, List, Mapping

from .base_loader import BaseDataContractLoader

logger = logging.getLogger(__name__)


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
    key: str  # 唯一标识符（如 'stock.kline.daily')
    type: str  # 'time_series' or 'non_time_series'
    scope: str  # 'global' or 'per_entity'
    display_name: str = ""  # 显示名称
    description: str = ""  # 描述
    unique_keys: List[str] = field(default_factory=list)  # 唯一键字段列表
    loader: Optional[Type[BaseDataContractLoader]] = None  # Loader 类

    @classmethod
    def from_dict(cls, meta: Dict[str, Any]) -> ContractMeta:
        """从字典创建 ContractMeta 实例。"""
        return cls(
            key=meta.get("key", ""),
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

    # 季度数据特有字段
    start_quarter: Optional[str] = None  # 起始季度（如 "2020Q1")
    end_quarter: Optional[str] = None  # 结束季度（如 "2020Q4")

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
            "start_quarter": runtime.get("start_quarter"),
            "end_quarter": runtime.get("end_quarter"),
        }

        # 额外字段（如 adjust, amount, direction 等）
        extra_fields = {}
        known_fields = set(base_fields.keys())
        for key, value in runtime.items():
            if key not in known_fields:
                extra_fields[key] = value

        if extra_fields:
            # 动态创建包含额外字段的 dataclass（使用 Any 类型注解）
            # 使用 __annotations__ 方式（Python 3.9兼容）
            annotations = {key: Any for key in extra_fields}
            extra_attrs = {
                "__annotations__": annotations,
                **{key: field(default=value) for key, value in extra_fields.items()}
            }
            runtime_cls = dataclass(type(
                "DynamicContractRuntime",
                (cls,),
                extra_attrs
            ))
            return runtime_cls(**base_fields)

        return cls(**base_fields)


@dataclass
class ContractSpecific:
    """Contract-specific metadata（特有字段，可选）。"""
    # 子类定义特有字段
    # 如果没有特有字段，使用默认空实例
    pass
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
class BaseDataContract:
    """DataContract 基类（meta/runtime/specific 三层结构）。"""

    meta: ContractMeta  # 静态信息
    runtime: ContractRuntime  # 动态信息
    specific: ContractSpecific  # 特有字段

    # identity
    contract_id: Optional[str] = None  # Contract ID（唯一标识符）

    # status
    data: Optional[Any] = None  # 数据缓存
    runtime_fingerprint: Optional[str] = None  # Runtime fingerprint（由 runtime 决定）
    is_loaded: bool = False  # 是否加载（data 是否有值）
    is_runtime_updated: bool = False  # runtime 是否更新（用于 fingerprint 验证）
    is_customized: bool = False  # 是否为用户自定义（系统=False，用户=True）

    def __init__(self, declaration: dict):
        """初始化 DataKey 实例。

        Args:
            declaration: 用户声明（包含 meta/specific，runtime 可选）
        """
        self.validate_declaration(declaration)
        self.meta = ContractMeta.from_dict(declaration.get("meta", {}))
        # runtime 可选（运行时注入）
        self.runtime = ContractRuntime.from_dict(declaration.get("runtime", {})) if "runtime" in declaration else ContractRuntime()
        # specific 可选（默认空实例）
        self.specific = ContractSpecific.from_dict(declaration.get("specific", {})) if declaration.get("specific") else ContractSpecific()
        
        # 生成 contract_id（基于 data_key + 时间戳，可选）
        import uuid
        # 生成 contract_id（基于 key + uuid，可选）
        if not self.contract_id:
            self.contract_id = f"{self.meta.key}_{uuid.uuid4().hex[:8]}"

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
        if "key" not in meta:
            raise ValueError("meta 缺少 'key' 字段")

        # 验证 meta
        self._validate_meta(meta)

        return True

    def add_runtime(self, runtime: dict) -> 'BaseDataContract':
        """添加运行时信息（支持链式调用，标记 runtime 已更新）。

        Args:
            runtime: 运行时信息字典

        Returns:
            self（支持链式调用）

        示例：
            contract.add_runtime({...}).fill_in_data()
        """
        self.runtime = ContractRuntime.from_dict(runtime)
        self._validate_runtime(runtime)
        
        # 标记 runtime 已更新（用于 fingerprint 验证）
        self.is_runtime_updated = True
        
        return self

    def is_global(self) -> bool:
        """检查 DataKey 是否为 GLOBAL scope。"""
        return self.meta.scope == ContractScope.GLOBAL

    def is_time_series(self) -> bool:
        """检查 DataKey 是否为 TIME_SERIES 类型。"""
        return self.meta.type == ContractType.TIME_SERIES

    def _calculate_runtime_fingerprint(self) -> str:
        """计算 runtime fingerprint（由整个 runtime 决定）。

        Returns:
            str: SHA256 fingerprint

        设计理念：
        - Fingerprint 由 runtime 决定（包含所有 runtime 字段）
        - 不包含 specific（specific 是静态声明，不影响缓存）
        """
        import hashlib
        import json

        # 提取 runtime 的所有字段
        runtime_data = {}
        for key, value in vars(self.runtime).items():
            # 过滤掉内部字段（如 __dict__, __weakref__ 等）
            if not key.startswith('_'):
                runtime_data[key] = value

        # 序列化并计算 SHA256
        fingerprint_str = json.dumps(runtime_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

    def _is_global_from_dict(self, meta: dict) -> bool:
        """从 meta dict 判断是否为 GLOBAL scope。"""
        return meta.get("scope") == ContractScope.GLOBAL

    def _is_time_series_from_dict(self, meta: dict) -> bool:
        """从 meta dict 判断是否为 TIME_SERIES 类型。"""
        return meta.get("type") == ContractType.TIME_SERIES

    def _validate_meta(self, meta: dict) -> None:
        """验证 ContractMeta 字段。"""
        if not meta.get("key"):
            raise ValueError("meta.key 不能为空")
        
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
                raise ValueError(f"Per entity contract {self.meta.key} 的 runtime 必须包含 entity_ids")
        
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
        """自动填充数据（根据 entity 数量选择加载方式，管理 runtime_fingerprint）。

        Args:
            runtime: 运行时信息（可选，如果提供则自动注入）
            force_reload: 是否强制重新加载（忽略 fingerprint）

        前提：
        - 必须有 runtime 信息（通过 add_runtime、declaration 或 runtime 参数提供）

        逻辑：
        - 如果提供了 runtime，标记 runtime 已更新
        - 只在 runtime 更新时才验证 fingerprint（已加载 + runtime 更新）
        - 如果 fingerprint 未变，直接返回（使用 cache）
        - 否则重新加载：
          - Global scope：调用 loader.load()
          - Per entity scope：
            - 单个 entity：调用 loader.load()
            - 多个 entity：调用 loader.load_batch()
        - 将数据存入 self.data，更新 runtime_fingerprint

        示例：
            # 方式1：链式调用
            contract.add_runtime({...}).fill_in_data()

            # 方式2：直接传参数
            contract.fill_in_data(runtime={...})
        """
        import logging
        logger = logging.getLogger(__name__)

        # 如果提供了 runtime 参数，先注入并标记 runtime 已更新
        if runtime is not None:
            self.add_runtime(runtime)

        # 检查 runtime 信息
        if self.meta.loader is None:
            raise ValueError(f"Contract {self.meta.key} 没有定义 loader")

        # Per entity scope：必须有 entity_ids
        if not self.is_global():
            entity_ids = self.get_entity_ids()
            if not entity_ids:
                raise ValueError(f"Per entity contract {self.meta.key} 需要 runtime.entity_ids（请调用 add_runtime 或提供 runtime 参数）")

        # Fingerprint 验证逻辑：只在已加载 + runtime 更新时才验证
        if not force_reload:
            # 如果未加载，直接加载（不验证 fingerprint）
            if not self.is_loaded:
                # 加载逻辑（下面）
                pass
            # 如果已加载但 runtime 未更新，直接返回（使用 cache）
            elif not self.is_runtime_updated:
                logger.debug(f"使用缓存数据: {self.meta.key}（runtime 未更新）")
                return
            # 如果已加载 + runtime 更新，验证 fingerprint
            else:
                # 计算 fingerprint 并验证
                current_fingerprint = self._calculate_runtime_fingerprint()

                # 如果 fingerprint 未变，直接返回（使用 cache）
                if self.runtime_fingerprint == current_fingerprint:
                    logger.debug(f"使用缓存数据: {self.meta.key}（fingerprint 未变）")
                    self.is_runtime_updated = False  # 标记 runtime 已验证
                    return

                # 如果 fingerprint 已变，需要刷新
                logger.debug(f"刷新数据: {self.meta.key}（fingerprint 已变）")

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

        # 标记已加载，更新 runtime_fingerprint
        self.is_loaded = True
        self.is_runtime_updated = False  # 标记 runtime 已验证
        self.runtime_fingerprint = self._calculate_runtime_fingerprint()

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
        if self.runtime.start_quarter is not None:
            params["start_quarter"] = self.runtime.start_quarter
        if self.runtime.end_quarter is not None:
            params["end_quarter"] = self.runtime.end_quarter

        # Runtime 动态字段（如 adjust, amount, direction 等）
        # 获取所有 runtime 字段，排除基础字段
        base_runtime_fields = {
            "start_time", "end_time", "entity_ids",
            "base_time_field", "time_format",
            "start_quarter", "end_quarter"
        }
        for key, value in self.runtime.__dict__.items():
            if not key.startswith("_") and key not in base_runtime_fields:
                # 动态字段直接传递给 loader
                params[key] = value

        return params

__all__ = ['BaseDataContract', 'ContractType', 'ContractScope', 'ContractMeta', 'ContractRuntime', 'ContractSpecific']