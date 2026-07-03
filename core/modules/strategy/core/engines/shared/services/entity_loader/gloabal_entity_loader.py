#!/usr/bin/env python3
"""全局数据管理中心（集中管理全局数据和缓存）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict, Union

from core.infra.project_context import ProjectContext
from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey
from core.modules.strategy.core.engines.shared.services.date_resolver.backtest_date_resolver import (
    resolve_latest_completed_trading_date,
)
from core.modules.strategy.core.engines.shared.services.entity_loader.stock_sampling import StockSampler
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
from core.modules.strategy.core.services.discovery.discovered_strategy import EnabledStrategyInfo

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


class GlobalEntityCache:
    """全局数据管理中心（集中管理全局数据和缓存）。

    职责：
    1. 解析 entity_ids（从 all_stocks + sampling 配置）
    2. 解析 settings，返回分组的数据声明（global 和 per_entity）
    3. 加载全局数据（issue global contracts，带数据）
    4. 管理缓存（避免重复加载）

    不负责：
    - per_entity contracts（由 job builder 在 build job 时 issue）
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        self.settings = settings
        self._global_data: Dict[str, Any] = {}
        self._global_meta: Dict[str, Any] = {}
        self._shm_name: Optional[str] = None
        self._shm_size: int = 0
        self._data_declarations = self.parse_settings(settings)
        self._global_declarations = self._data_declarations["global_declarations"]
        self._per_entity_declarations = self._data_declarations["per_entity_declarations"]

    @staticmethod
    def parse_settings(settings: Dict[str, Any]) -> DeclarationGroups:
        """解析 settings，找到所有数据声明，并根据 scope 分组。

        Args:
            settings: Settings dict

        Returns:
            DeclarationGroups：包含 global_declarations 和 per_entity_declarations

        流程：
        1. 解析 settings.data（使用 StrategyDataConfig）
        2. 从 issue_declarations() 获取所有声明（base + required）
        3. 使用 DataContracts().map.get() 获取每个声明的 spec
        4. 根据 spec["scope"] 分组为 global 和 per_entity
        """
        # 使用 StrategyDataConfig 解析 settings.data
        from core.modules.strategy.core.engines.shared.services.entity_loader.strategy_data_resolver import StrategyDataResolver
        
        data_config = StrategyDataResolver(settings)
        declarations = data_config.issue_declarations()  # 返回 base + required 的声明列表
        
        dcm = DataContracts()
        global_declarations: List[DataDeclaration] = []
        per_entity_declarations: List[DataDeclaration] = []
        
        for raw_item in declarations:
            data_key = str(raw_item.get("data_key") or "").strip()
            if not data_key:
                logger.warning("数据声明缺少 data_key，跳过")
                continue
            
            params = dict(raw_item.get("params") or {})
            indicators = dict(raw_item.get("indicators") or {})
            
            # 从 DataContracts 获取 spec
            dk = DataKey(data_key)
            spec = dcm.map.get(dk)
            
            if spec is None:
                logger.warning(f"未注册的 data_key：{data_key}，跳过")
                continue
            
            scope = spec.get("scope")
            if scope not in ("global", "per_entity"):
                logger.warning(f"data_key={data_key} 的 scope={scope} 未知，跳过")
                continue
            
            declaration: DataDeclaration = {
                "data_key": data_key,
                "params": params,
                "indicators": indicators,
                "scope": scope,
            }
            
            if scope == "global":
                global_declarations.append(declaration)
            else:
                per_entity_declarations.append(declaration)
        
        logger.info(
            f"parse_settings() 完成：global={len(global_declarations)}，"
            f"per_entity={len(per_entity_declarations)}"
        )
        
        return {
            "global_declarations": global_declarations,
            "per_entity_declarations": per_entity_declarations,
        }

    @staticmethod
    def resolve_entity_ids(
        strategy_info: EnabledStrategyInfo,
        effective_settings: Union[StrategySettings, Dict[str, Any]],
    ) -> List[str]:
        """解析 entity_ids（从 all_stocks + sampling 配置）。

        Args:
            strategy_info: EnabledStrategyInfo 对象（包含 strategy key）
            effective_settings: StrategySettings 对象或 dict（包含 sampling 配置）

        Returns:
            entity_ids 列表

        流程（参考 legacy strategy）：
        1. 从 DataContract 加载全量股票列表（all_stocks）
        2. 判断是否开启采样（use_sampling）
        3. 采样开启：调用 StockSamplingHelper.get_stock_list()
        4. 采样关闭：直接返回全量股票ID

        设计：
        - entity_ids 是全局配置的一部分（影响所有 jobs）
        - 用于 fingerprint 生成和 job builder 构建 jobs
        """
        # 1. 从 DataContract 加载全量股票列表（contract 形式）
        stock_list = GlobalEntityCache._load_stock_list()
        if not stock_list:
            logger.warning("stock_list 为空，返回空 entity_ids")
            return []

        # 2. 获取 sampling 配置
        if isinstance(effective_settings, StrategySettings):
            raw_settings = effective_settings.raw_settings
        else:
            raw_settings = dict(effective_settings or {})
        
        sampling = raw_settings.get("sampling", {})
        use_sampling = sampling.get("use_sampling", False)

        # 3. 采样开启：调用 StockSampler
        if use_sampling:
            sampling_amount = sampling.get("sampling_amount", 10)
            sampling_strategy = sampling.get("strategy", "continuous")
            
            logger.info(
                f"采样开启：sampling_amount={sampling_amount}, "
                f"sampling_strategy={sampling_strategy}"
            )
            
            # 构造完整的 sampling_config
            full_sampling_config = {
                "strategy": sampling_strategy,
                "sampling_amount": sampling_amount,
                **sampling,  # 包含所有子配置（pool、blacklist等）
            }
            
            return StockSampler.sample(
                stock_list=[s["id"] for s in all_stocks],
                sampling_config=full_sampling_config,
                strategy_name=strategy_info.key,
            )

        # 4. 采样关闭：返回全量股票ID
        logger.info(f"采样关闭：返回全量股票ID，数量={len(all_stocks)}")
        return [s["id"] for s in all_stocks if s.get("id")]

    @staticmethod
    def _load_stock_list() -> List[Dict[str, Any]]:
        """从 DataContract 加载全量股票列表（contract 形式）。

        Returns:
            all_stocks 列表（List[Dict[str, Any]]，包含 id、name 等字段）

        设计：
        - 使用 DataContracts.issue(DataKey.STOCK_LIST)
        - 返回全量股票信息（不仅仅是 ID，还包含 name、industry 等）
        - contract 形式（统一数据接口）
        """
        try:
            dcm = DataContracts()
            contract = dcm.issue(DataKey.STOCK_LIST)
            
            if contract.needs_load:
                # 如果 contract 需要加载，执行加载
                contract.load()
            
            all_stocks = list(contract.data or [])
            
            logger.info(f"加载全量股票列表成功：数量={len(all_stocks)}")
            return all_stocks
            
        except Exception as e:
            logger.error(f"加载全量股票列表失败：{e}", exc_info=True)
            return []

    @staticmethod
    def load_latest_completed_trading_date() -> str:
        """加载最新已完成交易日（API 形式，非 contract）。

        Returns:
            latest_completed_trading_date（日期字符串，例如 "20240101")

        设计：
        - 使用 DataManager API 直接获取（非 contract 形式）
        - latest_completed_trading_date 是简单的日期字符串，不适合作为 contract
        - API 形式更简单高效
        """
        try:
            from core.modules.data_manager import DataManager
            
            data_mgr = DataManager(is_verbose=False)
            latest_date = resolve_latest_completed_trading_date(data_mgr)
            
            logger.info(f"加载最新已完成交易日成功：{latest_date}")
            return latest_date
            
        except Exception as e:
            logger.error(f"加载最新已完成交易日失败：{e}", exc_info=True)
            return ""

    def preload_global_data(
        self,
        start_date: str,
        end_date: str,
        entity_ids: List[str],
        **kwargs,
    ) -> None:
        """填补缓存里没有的全局数据（contract 形式）。

        Args:
            start_date: 开始日期
            end_date: 结束日期
            entity_ids: Entity ID 列表（某些 global data 可能依赖）
            **kwargs: 其他参数

        流程：
        1. 检查 global_declarations
        2. 对每个 global declaration，issue contract（带数据）
        3. 使用 DataContracts.issue() 加载全局数据
        4. 缓存到 _global_data

        设计：
        - 只处理 global contracts（per_entity contracts 由 job builder 处理）
        - 使用 contract.load() 加载全局数据
        - 全局数据加载后存入 _global_data（用于共享内存）
        """
        logger.info(
            f"preload_global_data() 开始：global_declarations={len(self._global_declarations)}"
        )
        
        dcm = DataContracts()
        
        for declaration in self._global_declarations:
            data_key = declaration["data_key"]
            params = declaration["params"]
            
            logger.info(f"加载全局数据：data_key={data_key}")
            
            try:
                # 使用 DataContracts.issue() 加载全局数据
                contract = dcm.issue(
                    DataKey(data_key),
                    start=start_date,
                    end=end_date,
                    **params,
                )
                
                # 如果 contract 需要加载，执行加载
                if contract.needs_load:
                    contract.load()
                
                # 缓存到 _global_data
                self._global_data[data_key] = list(contract.data or [])
                
                logger.info(f"全局数据加载成功：data_key={data_key}, 数据量={len(contract.data or [])}")
                
            except Exception as e:
                logger.error(f"全局数据加载失败：data_key={data_key}, error={e}", exc_info=True)
                # 失败时缓存空数据
                self._global_data[data_key] = []
        
        # 更新 meta 信息
        self._global_meta.update({
            "start_date": start_date,
            "end_date": end_date,
            "entity_ids_count": len(entity_ids),
            "global_declarations_count": len(self._global_declarations),
            "per_entity_declarations_count": len(self._per_entity_declarations),
            "loaded_global_keys": list(self._global_data.keys()),
        })
        
        logger.info(f"preload_global_data() 完成：已加载 {len(self._global_data)} 个全局数据")

    def get_global_declarations(self) -> List[DataDeclaration]:
        """获取全局数据声明列表。"""
        return list(self._global_declarations)

    def get_per_entity_declarations(self) -> List[DataDeclaration]:
        """获取 per_entity 数据声明列表。"""
        return list(self._per_entity_declarations)

    def get_global_data(self) -> Dict[str, Any]:
        """获取已加载的全局数据。"""
        return dict(self._global_data)

    def get_global_meta(self) -> Dict[str, Any]:
        """获取全局数据 metadata。"""
        return dict(self._global_meta)


__all__ = ["GlobalEntityCache", "DataDeclaration", "DeclarationGroups"]