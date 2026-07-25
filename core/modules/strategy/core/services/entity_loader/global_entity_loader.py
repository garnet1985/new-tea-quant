"""全局 entity 数据加载与共享内存（entity_loader 整块之一）。

消费者: enumerator
其它: Facade, fingerprints
（整块消费者见 entity_loader/__init__.py）

本文件:
- GlobalEntityCache: 系统 global（stock.list / trade.calendar / latest date）+ 策略 global + shm
  边界: 负责加载与 shm；不负责 settings.data 解析（StrategyDataResolver）或 per_entity bundle
"""

from __future__ import annotations

import logging
import pickle
from typing import Any, Dict, List, Optional

from core.modules.data_contract import ContractIssuer, DATA_KEY
from core.modules.strategy.core.services.entity_loader.strategy_data_resolver import (
    SYSTEM_GLOBAL_DATA_KEYS,
    DataDeclaration,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

logger = logging.getLogger(__name__)

try:
    from multiprocessing.shared_memory import SharedMemory

    SHARED_MEMORY_AVAILABLE = True
except ImportError:
    logger.warning("multiprocessing.shared_memory 不可用，将使用普通 dict 存储")
    SHARED_MEMORY_AVAILABLE = False


class GlobalEntityCache:
    """全局数据加载器 + 共享内存缓存。"""

    def __init__(self, settings: StrategySettings) -> None:
        self._settings = settings
        self._global_data: Dict[str, Any] = {}
        self._global_meta: Dict[str, Any] = {}
        self._shm_name: Optional[str] = None
        self._shm_size: int = 0

    def init_system_globals(self) -> "GlobalEntityCache":
        """加载三个系统级 global 数据（不走 settings.data 分组，必定存在）。"""
        latest_date = self.load_latest_completed_trading_date()
        self._global_meta["latest_completed_trading_date"] = latest_date
        return self.init_stock_list().init_trade_calendar()

    def init_stock_list(self) -> "GlobalEntityCache":
        """加载 stock_list 并写入缓存。"""
        try:
            contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
            stock_list = list(contract.get_data() or [])
            self._global_data[DATA_KEY.STOCK_LIST] = stock_list
            logger.info("加载 stock_list 成功：数量=%d", len(stock_list))
        except Exception as exc:
            logger.error("加载 stock_list 失败：%s", exc, exc_info=True)
            self._global_data[DATA_KEY.STOCK_LIST] = []
        return self

    def init_trade_calendar(self) -> "GlobalEntityCache":
        """加载 trade_calendar 并写入缓存（日期来自 settings.simulation）。"""
        try:
            start_date, end_date = self._resolve_simulation_date_range()
            contract = ContractIssuer.issue(
                DATA_KEY.TRADE_CALENDAR,
                runtime={"start": start_date, "end": end_date},
                fill_in_data=True,
            )
            trade_calendar = list(contract.get_data() or [])
            self._global_data[DATA_KEY.TRADE_CALENDAR] = trade_calendar
            logger.info(
                "加载 trade_calendar 成功：start=%s, end=%s, 数量=%d",
                start_date,
                end_date,
                len(trade_calendar),
            )
        except Exception as exc:
            logger.error("加载 trade_calendar 失败：%s", exc, exc_info=True)
            self._global_data[DATA_KEY.TRADE_CALENDAR] = []
        return self

    def get_stock_ids(self) -> List[str]:
        """返回缓存中的 stock id 列表。"""
        stock_list = self._global_data.get(DATA_KEY.STOCK_LIST)
        if not stock_list:
            self.init_stock_list()
            stock_list = self._global_data.get(DATA_KEY.STOCK_LIST, [])
        return [stock.get("id") for stock in stock_list if stock.get("id")]

    @staticmethod
    def get_stock_list() -> List[str]:
        """加载全市场股票 id 列表（不依赖策略 settings；供编排层算指纹）。"""
        try:
            contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
            rows = list(contract.get_data() or [])
            return [str(row.get("id")).strip() for row in rows if row.get("id")]
        except Exception as exc:
            logger.error("get_stock_list 失败：%s", exc, exc_info=True)
            return []

    @staticmethod
    def get_latest_completed_trading_date() -> str:
        """最新已完成交易日（与 load_latest_completed_trading_date 同源）。"""
        return GlobalEntityCache.load_latest_completed_trading_date()

    def seed_system_globals(
        self,
        *,
        stock_list: Optional[List[str]] = None,
        latest_completed_trading_date: Optional[str] = None,
    ) -> "GlobalEntityCache":
        """用编排层已取好的 stock / latest_date 填充缓存，避免重复 IO。"""
        if latest_completed_trading_date is None:
            latest_completed_trading_date = self.load_latest_completed_trading_date()
        self._global_meta["latest_completed_trading_date"] = str(
            latest_completed_trading_date or ""
        )

        if stock_list is None:
            self.init_stock_list()
        else:
            self._global_data[DATA_KEY.STOCK_LIST] = [
                {"id": str(stock_id).strip()}
                for stock_id in stock_list
                if str(stock_id).strip()
            ]
        return self

    def load_global_declarations(self, global_declarations: List[DataDeclaration]) -> None:
        """按 StrategyDataResolver 分组结果加载 global 数据，并写入共享内存。"""
        if not global_declarations:
            logger.info("无 global 数据声明，仅同步已有缓存到共享内存")
            self._create_shared_memory()
            return

        logger.info("开始加载 %d 个 global 数据", len(global_declarations))
        self._load_global_data(global_declarations)
        self._create_shared_memory()

    def _resolve_simulation_date_range(self) -> tuple[str, str]:
        """与 StrategySettings.resolve_period 一致：读 simulation.start/end。"""
        period = self._settings.resolve_period()
        return str(period.start_date), str(period.end_date)

    def _load_global_data(self, declarations: List[DataDeclaration]) -> None:
        for decl in declarations:
            data_key = decl.get("data_key")
            if not data_key:
                logger.warning("数据声明缺少 data_key: %s", decl)
                continue
            if data_key in SYSTEM_GLOBAL_DATA_KEYS:
                logger.debug("跳过系统 global 数据（已由 init_system_globals 加载）: %s", data_key)
                continue

            params = dict(decl.get("params") or {})
            try:
                contract = ContractIssuer.issue(data_key, runtime=params, fill_in_data=True)
                data = contract.get_data()
                self._global_data[data_key] = data
                self._global_meta[data_key] = {
                    "params": params,
                    "contract_type": contract.meta.type,
                    "contract_scope": contract.meta.scope,
                }
                size_hint = len(data) if isinstance(data, (list, dict)) else "N/A"
                logger.info("加载 global 数据成功: %s, 数据量=%s", data_key, size_hint)
            except Exception as exc:
                logger.error("加载 global 数据失败: %s, 错误: %s", data_key, exc, exc_info=True)

    @staticmethod
    def load_latest_completed_trading_date() -> str:
        """返回最新已完成交易日（DataManager API）。"""
        try:
            from core.modules.data_manager import DataManager

            data_mgr = DataManager(is_verbose=False)
            latest_date = data_mgr.service.calendar.get_latest_completed_trading_date()
            logger.info("加载最新已完成交易日成功：%s", latest_date)
            return latest_date
        except Exception as exc:
            logger.error("加载最新已完成交易日失败：%s", exc, exc_info=True)
            return ""

    def _create_shared_memory(self) -> None:
        if not SHARED_MEMORY_AVAILABLE:
            logger.warning("共享内存不可用，使用普通 dict 存储")
            return
        if not self._global_data:
            logger.warning("没有全局数据，跳过共享内存创建")
            return

        try:
            serialized_data = pickle.dumps(self._global_data)
            data_size = len(serialized_data)
            shm = SharedMemory(create=True, size=data_size)
            shm.buf[:data_size] = serialized_data
            self._shm_name = shm.name
            self._shm_size = data_size
            logger.info(
                "共享内存创建成功：name=%s, size=%d bytes, keys=%d",
                shm.name,
                data_size,
                len(self._global_data),
            )
            shm.close()
        except Exception as exc:
            logger.error("共享内存创建失败：%s", exc, exc_info=True)
            self._shm_name = None
            self._shm_size = 0

    @staticmethod
    def access_shared_memory(shm_name: str, shm_size: int) -> Dict[str, Any]:
        """子进程从共享内存读取 global 数据。"""
        if not SHARED_MEMORY_AVAILABLE:
            logger.warning("共享内存不可用，无法读取")
            return {}
        if not shm_name or shm_size <= 0:
            logger.warning("共享内存信息无效，无法读取")
            return {}

        try:
            shm = SharedMemory(name=shm_name)
            serialized_data = bytes(shm.buf[:shm_size])
            global_data = pickle.loads(serialized_data)
            shm.close()
            logger.info(
                "共享内存读取成功：name=%s, size=%d bytes, keys=%d",
                shm_name,
                shm_size,
                len(global_data),
            )
            return global_data
        except Exception as exc:
            logger.error("共享内存读取失败：%s", exc, exc_info=True)
            return {}

    def cleanup(self) -> None:
        """主进程释放共享内存。"""
        if not SHARED_MEMORY_AVAILABLE or not self._shm_name:
            return
        try:
            shm = SharedMemory(name=self._shm_name)
            shm.close()
            shm.unlink()
            logger.info("共享内存释放成功：name=%s", self._shm_name)
            self._shm_name = None
            self._shm_size = 0
        except Exception as exc:
            logger.error("共享内存释放失败：%s", exc, exc_info=True)

    def get_shm_info(self) -> Dict[str, Any]:
        return {
            "shm_name": self._shm_name or "",
            "shm_size": self._shm_size or 0,
        }

    def get_trade_calendar(self) -> List[Any]:
        """返回已加载的 trade.calendar 行（主进程规划 timeline 用）。"""
        from core.modules.data_contract import DATA_KEY

        rows = self._global_data.get(DATA_KEY.TRADE_CALENDAR)
        return list(rows or [])


__all__ = ["GlobalEntityCache"]
