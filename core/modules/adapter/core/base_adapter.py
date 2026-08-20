#!/usr/bin/env python3
"""BaseOpportunityAdapter — 机会适配器基类。

职责：
- 定义 adapter 接口
- 提供基础功能（配置加载、日志等）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import logging
import importlib

from core.modules.adapter.core.loader import AdapterLoader

if TYPE_CHECKING:
    # 勿在运行时 import strategy.contracts：会经 scanner→adapter 形成环
    from core.modules.strategy.contracts import Opportunity

logger = logging.getLogger(__name__)


class BaseOpportunityAdapter(ABC):
    """
    机会适配器基类

    用户需要继承此类并实现 process 方法。
    基类提供：
    - 配置加载（从 settings.py）
    - 日志记录
    - 基础工具方法
    """

    def __init__(self, adapter_name: Optional[str] = None):
        """
        初始化 adapter

        Args:
            adapter_name: 适配器名称（如果不提供，会从类名推断）
        """
        self.adapter_name = adapter_name or self._infer_adapter_name()
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()

    def _infer_adapter_name(self) -> str:
        """从类名推断 adapter 名称"""
        class_name = self.__class__.__name__
        if class_name.endswith("Adapter"):
            class_name = class_name[:-7]
        if class_name.endswith("Opportunity"):
            class_name = class_name[:-11]
        return class_name.lower()

    def _load_config(self) -> None:
        """加载 adapter 配置（从 settings.py）"""
        try:
            module_path = AdapterLoader.settings_module_path(self.adapter_name)
            settings_module = importlib.import_module(module_path)

            if hasattr(settings_module, "settings"):
                self._config = getattr(settings_module, "settings", {})
            elif hasattr(settings_module, "config"):
                self._config = getattr(settings_module, "config", {})
            else:
                self._config = {}
                logger.debug(
                    f"[BaseOpportunityAdapter] {self.adapter_name} 没有找到 settings/config，使用空配置"
                )
        except ModuleNotFoundError:
            self._config = {}
            logger.debug(
                f"[BaseOpportunityAdapter] {self.adapter_name} 没有 settings.py，使用空配置"
            )
        except Exception as e:
            logger.warning(
                f"[BaseOpportunityAdapter] 加载 {self.adapter_name} 配置失败: {e}"
            )
            self._config = {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        if self._config is None:
            self._load_config()
        return self._config or {}

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键（支持点号分隔，如 "output.format"）
            default: 默认值

        Returns:
            配置值
        """
        config = self.config
        keys = key.split(".")
        for k in keys:
            if isinstance(config, dict):
                config = config.get(k)
                if config is None:
                    return default
            else:
                return default
        return config if config is not None else default

    @abstractmethod
    def process(
        self,
        opportunities: List[Opportunity],
        context: Dict[str, Any],
    ) -> None:
        """
        处理机会列表（用户必须实现）

        Args:
            opportunities: 机会列表（已转换为 Opportunity dataclass）
            context: 上下文信息
                - date: 扫描日期
                - strategy_name: 策略名称
                - scan_summary: 扫描汇总统计
        """
        pass

    def log_info(self, message: str) -> None:
        """记录信息日志"""
        logger.info(f"[{self.adapter_name}] {message}")

    def log_warning(self, message: str) -> None:
        """记录警告日志"""
        logger.warning(f"[{self.adapter_name}] {message}")

    def log_error(self, message: str, exc_info: bool = False) -> None:
        """记录错误日志"""
        logger.error(f"[{self.adapter_name}] {message}", exc_info=exc_info)

    @staticmethod
    def format_scalar_price(v: Any) -> str:
        """CSV/JSON 反序列化后价格可能为 str，避免 f-string 使用 ``:.2f`` 抛错。"""
        if v is None or v == "":
            return ""
        try:
            return f"{float(v):.2f}"
        except (TypeError, ValueError):
            return str(v)

    @staticmethod
    def default_output(
        opportunities: List[Opportunity],
        context: Dict[str, Any],
    ) -> None:
        """
        默认输出方法（当所有配置的 adapter 都失败时使用）

        输出简单的机会信息：
        - 机会时间
        - 策略名
        - 基本的价格或价格区间
        """
        date = context.get("date", "unknown")
        strategy_name = context.get("strategy_name", "unknown")
        date_meta = (
            context.get("date_meta")
            if isinstance(context.get("date_meta"), dict)
            else {}
        )

        print("\n" + "=" * 60)
        print("扫描结果（默认输出）")
        print("=" * 60)
        print(f"策略: {strategy_name}")
        print(f"日期: {date}")
        mode_label = str(date_meta.get("mode_label") or "").strip()
        detail = str(date_meta.get("source_detail") or "").strip()
        if mode_label:
            print(f"日期模式: {mode_label}")
        if detail:
            print(f"日期来源: {detail}")
        print(f"机会数: {len(opportunities)}")
        print("=" * 60)

        if not opportunities:
            print("\n[默认输出] 没有发现任何机会")
            print("=" * 60)
            return

        for i, opp in enumerate(opportunities, 1):
            print(f"\n【机会 {i}】")
            print(f"  股票: {opp.stock_name} ({opp.stock_id})")
            print(f"  时间: {opp.trigger_date}")

            if opp.trigger_price:
                px = BaseOpportunityAdapter.format_scalar_price(opp.trigger_price)
                if px:
                    print(f"  价格: {px}")

            if opp.signal_snapshot:
                print(f"  信号快照: {opp.signal_snapshot}")

        print("\n" + "=" * 60)


__all__ = ["BaseOpportunityAdapter"]
