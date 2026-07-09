#!/usr/bin/env python3
"""全局数据管理中心（集中管理全局数据和缓存）。

职责：
1. 加载全局数据（global contracts）
2. 管理共享内存（避免重复传输）
3. 不负责 entity_ids 解析（由 StockSampler 处理）
4. 不负责数据声明解析（由 StrategyDataResolver 处理）
"""

from __future__ import annotations

import logging
import pickle
from typing import Any, Dict, List, Optional, TypedDict

from core.infra.project_context import ProjectContext
from core.modules.data_contract import ContractIssuer, DATA_KEY

logger = logging.getLogger(__name__)

try:
    from multiprocessing.shared_memory import SharedMemory
    SHARED_MEMORY_AVAILABLE = True
except ImportError:
    logger.warning("multiprocessing.shared_memory 不可用，将使用普通 dict 存储")
    SHARED_MEMORY_AVAILABLE = False


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

    is_initialized: bool = False

    def __init__(
        self,
        settings: StrategySettings,  # StrategySettings
    ) -> None:
        """初始化 GlobalEntityCache。

        Args:
            settings: 策略设置对象

        职责：
        - 只负责全局数据的管理和缓存
        - 不负责 entity_ids 解析（由 StockSampler 处理）
        - 不负责数据声明解析（由 StrategyDataResolver 处理）
        """
        self._settings = settings
        self._global_data: Dict[str, Any] = {}
        self._global_meta: Dict[str, Any] = {}
        self._global_declarations: List[DataDeclaration] = []
        self._per_entity_declarations: List[DataDeclaration] = []
        self._shm_name: Optional[str] = None
        self._shm_size: int = 0
        
    def init_stock_list(self) -> "GlobalEntityCache":
        """初始化stock_list contract并缓存数据（使用ContractIssuer.issue()）。

        Returns:
            stock_list数据（包含id、name、industry等信息）

        设计：
        - 使用ContractIssuer.issue(DATA_KEY.STOCK_LIST)简化API
        - stock_list是系统内置contract，强制加载
        - fill_in_data=True显式加载
        - 使用get_data()获取数据
        - 缓存到self._global_data中
        """
        try:
            # 使用新的issue API（自动discovery + 加载）
            contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
            stock_list = list(contract.get_data() or [])

            # 缓存数据
            self._global_data[DATA_KEY.STOCK_LIST] = stock_list

            logger.info(f"加载stock_list成功：数量={len(stock_list)}")

            return self

        except Exception as e:
            logger.error(f"加载stock_list失败：{e}", exc_info=True)
            self._global_data[DATA_KEY.STOCK_LIST] = []

            return self

    def init_trade_calendar(self) -> "GlobalEntityCache":
        """初始化trade_calendar contract并缓存数据。

        Returns:
            self（支持方法链）

        设计：
        - 从settings.sampling获取start_date和end_date
        - trade_calendar是回测必需的系统数据，强制加载
        - 使用ContractIssuer.issue()加载
        - 缓存到self._global_data中
        """
        try:
            # 从sampling字段获取日期范围
            sampling = self._settings.raw_settings.get("sampling", {})
            start_date = sampling.get("start_date")
            end_date = sampling.get("end_date")

            # 如果没有end_date，使用latest completed trading date
            if not end_date:
                end_date = self.load_latest_completed_trading_date()
                logger.info(f"sampling未配置end_date，使用latest completed trading date: {end_date}")

            # 如果没有start_date，使用默认值
            if not start_date:
                start_date = "20200101"
                logger.info(f"sampling未配置start_date，使用默认值: {start_date}")

            # 使用ContractIssuer.issue()加载trade_calendar
            contract = ContractIssuer.issue(
                DATA_KEY.TRADE_CALENDAR,
                runtime={
                    "start": start_date,
                    "end": end_date,
                },
                fill_in_data=True,
            )

            trade_calendar = list(contract.get_data() or [])

            # 缓存数据
            self._global_data[DATA_KEY.TRADE_CALENDAR] = trade_calendar

            logger.info(
                f"加载trade_calendar成功：start={start_date}, end={end_date}, "
                f"数量={len(trade_calendar)}"
            )

            return self

        except Exception as e:
            logger.error(f"加载trade_calendar失败：{e}", exc_info=True)
            self._global_data[DATA_KEY.TRADE_CALENDAR] = []

            return self

    def get_stock_ids(self) -> List[str]:
        """获取缓存中的stock_ids。

        Returns:
            stock_ids列表（如["600000.SH", "600001.SH"]）
        """
        stock_list = self._global_data.get(DATA_KEY.STOCK_LIST)
        if not stock_list:
            self.init_stock_list()
        stock_ids = [stock.get("id") for stock in stock_list if stock.get("id")]
        return stock_ids

    def load_required_data(self) -> None:
        """加载settings中需要的全局数据。
        
        流程：
        1. 从settings.raw_settings中获取data字段
        2. 解析data字段中的数据声明（base、required等）
        3. 使用ContractIssuer获取contract meta，判断是否为global
        4. 加载global数据并缓存到self._global_data
        """
        # Step 1: 获取data字段（已validate，直接获取）
        data_section = self._settings.raw_settings.get("data", {})
        
        if not data_section:
            logger.info("settings中没有data字段，无需加载全局数据")
            return
        
        # Step 2: 解析数据声明
        declarations = self._get_data_declarations(data_section)
        
        if not declarations:
            logger.info("没有数据声明，无需加载")
            return
        
        # Step 3: 筛选global和per_entity声明
        global_declarations = []
        per_entity_declarations = []
        
        for decl in declarations:
            data_key = decl.get("data_key")
            if not data_key:
                logger.warning(f"数据声明缺少data_key: {decl}")
                continue
            
            # 使用ContractIssuer.is_global()判断（不创建instance）
            try:
                if ContractIssuer.is_global(data_key):
                    global_declarations.append(decl)
                    logger.debug(f"发现global数据: {data_key}")
                else:
                    per_entity_declarations.append(decl)
                    logger.debug(f"发现per_entity数据: {data_key}")
            except Exception as e:
                logger.warning(f"判断contract scope失败: {data_key}, 错误: {e}")
        
        # 保存声明分组（供后续使用）
        self._global_declarations = global_declarations
        self._per_entity_declarations = per_entity_declarations

        if not global_declarations:
            logger.info("没有需要加载的global数据")
            # 即使没有global_declarations，也需要写入共享内存（包含stock_list和trade_calendar）
            self._create_shared_memory()
            return

        # Step 4: 加载global数据
        logger.info(f"开始加载{len(global_declarations)}个global数据")
        self._load_global_data(global_declarations)

        # Step 5: 将所有global数据写入共享内存（包括stock_list和trade_calendar）
        self._create_shared_memory()
    
    def _get_data_declarations(self, data_section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从data字段解析数据声明。
        
        Args:
            data_section: settings中的data字段
            
        Returns:
            数据声明列表（包含data_key、params、indicators）
        
        结构：
        - base: 基础数据声明
        - required: 额外必需的数据声明列表
        
        字段名：
        - data_key（实际策略使用）
        - params: 数据加载参数
        - indicators: 数据后处理指标
        """
        declarations = []
        
        # 解析base声明
        base_decl = data_section.get("base")
        if base_decl:
            declarations.append(base_decl)
        
        # 解析required声明列表
        required_decls = data_section.get("required", [])
        if required_decls:
            declarations.extend(required_decls)
        
        return declarations
    
    def _load_global_data(self, declarations: List[Dict[str, Any]]) -> None:
        """批量加载global数据。
        
        Args:
            declarations: global数据声明列表
        
        流程：
        1. 遍历每个declaration
        2. 使用ContractIssuer.issue()加载数据
        3. 缓存到self._global_data
        
        字段：
        - data_key: contract key（如"stock.kline.daily"）
        - params: 数据加载参数（如{"adjust": "qfq"}）
        - indicators: 数据后处理指标（暂不处理）
        """
        for decl in declarations:
            data_key = decl.get("data_key")
            if not data_key:
                logger.warning(f"数据声明缺少data_key: {decl}")
                continue
            
            params = decl.get("params", {})
            
            try:
                # 加载数据（使用params）
                contract = ContractIssuer.issue(data_key, runtime=params, fill_in_data=True)
                data = contract.get_data()
                
                # 缓存数据
                self._global_data[data_key] = data
                
                # 记录meta信息
                self._global_meta[data_key] = {
                    "params": params,
                    "contract_type": contract.meta.type,
                    "contract_scope": contract.meta.scope,
                }
                
                logger.info(f"加载global数据成功: {data_key}, 数据量={len(data) if isinstance(data, (list, dict)) else 'N/A'}")
                
            except Exception as e:
                logger.error(f"加载global数据失败: {data_key}, 错误: {e}", exc_info=True)

    @staticmethod
    def load_latest_completed_trading_date() -> str:
        """加载最新已完成交易日（直接使用 DataManager API）。

        Returns:
            latest_completed_trading_date（日期字符串，例如 "20240101")

        设计：
        - 直接调用 DataManager.service.calendar.get_latest_completed_trading_date()
        - 简单日期字符串，不适合作为 contract
        - API 形式更简单高效
        """
        try:
            from core.modules.data_manager import DataManager
            
            data_mgr = DataManager(is_verbose=False)
            latest_date = data_mgr.service.calendar.get_latest_completed_trading_date()
            
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
        
        # 将全局数据序列化到共享内存
        self._create_shared_memory()

    def _create_shared_memory(self) -> None:
        """将全局数据序列化到共享内存（用于子进程访问）。"""
        if not SHARED_MEMORY_AVAILABLE:
            logger.warning("共享内存不可用，使用普通 dict 存储")
            return
        
        if not self._global_data:
            logger.warning("没有全局数据，跳过共享内存创建")
            return
        
        try:
            # 序列化全局数据
            serialized_data = pickle.dumps(self._global_data)
            data_size = len(serialized_data)
            
            # 创建共享内存
            shm = SharedMemory(create=True, size=data_size)
            
            # 写入数据
            shm.buf[:data_size] = serialized_data
            
            # 记录共享内存信息（用于传递给子进程）
            self._shm_name = shm.name
            self._shm_size = data_size
            
            logger.info(
                f"共享内存创建成功：name={shm.name}, size={data_size} bytes, "
                f"包含 {len(self._global_data)} 个全局数据"
            )
            
            # 关闭共享内存（但不释放，子进程需要访问）
            shm.close()
            
        except Exception as e:
            logger.error(f"共享内存创建失败：{e}", exc_info=True)
            self._shm_name = None
            self._shm_size = 0

    @staticmethod
    def access_shared_memory(shm_name: str, shm_size: int) -> Dict[str, Any]:
        """从共享内存读取全局数据（子进程调用）。

        Args:
            shm_name: 共享内存名称
            shm_size: 共享内存大小（bytes）

        Returns:
            全局数据字典

        使用场景：
        - 子进程通过 shm_name 和 shm_size 访问主进程创建的共享内存
        - 避免 pickle 重复传输全局数据
        """
        if not SHARED_MEMORY_AVAILABLE:
            logger.warning("共享内存不可用，无法读取")
            return {}
        
        if not shm_name or shm_size <= 0:
            logger.warning("共享内存信息无效，无法读取")
            return {}
        
        try:
            # 访问共享内存
            shm = SharedMemory(name=shm_name)
            
            # 读取数据
            serialized_data = bytes(shm.buf[:shm_size])
            
            # 反序列化
            global_data = pickle.loads(serialized_data)
            
            logger.info(
                f"共享内存读取成功：name={shm_name}, size={shm_size} bytes, "
                f"包含 {len(global_data)} 个全局数据"
            )
            
            # 关闭共享内存（但不释放）
            shm.close()
            
            return global_data
            
        except Exception as e:
            logger.error(f"共享内存读取失败：{e}", exc_info=True)
            return {}

    def cleanup(self) -> None:
        """释放共享内存（主进程调用）。"""
        if not SHARED_MEMORY_AVAILABLE:
            return
        
        if not self._shm_name:
            logger.warning("没有共享内存，跳过释放")
            return
        
        try:
            # 释放共享内存
            shm = SharedMemory(name=self._shm_name)
            shm.close()
            shm.unlink()  # 释放共享内存
            
            logger.info(f"共享内存释放成功：name={self._shm_name}")
            
            self._shm_name = None
            self._shm_size = 0
            
        except Exception as e:
            logger.error(f"共享内存释放失败：{e}", exc_info=True)

    def get_shm_info(self) -> Optional[Dict[str, Any]]:
        """获取共享内存信息（用于传递给子进程）。"""
        if not self._shm_name or self._shm_size <= 0:
            return None
        
        return {
            "shm_name": self._shm_name,
            "shm_size": self._shm_size,
        }

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

    def get_shm_info(self) -> Dict[str, Any]:
        """获取共享内存信息（用于传递给子进程）。"""
        return {
            "shm_name": self._shm_name or "",
            "shm_size": self._shm_size or 0,
        }

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """根据 key 获取全局数据。"""
        return self._global_data.get(key)


__all__ = ["GlobalEntityCache", "DataDeclaration", "DeclarationGroups"]