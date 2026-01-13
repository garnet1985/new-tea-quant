#!/usr/bin/env python3
"""
SimulatorHooksDispatcher

职责：
- 根据 strategy_name 动态加载 userspace 的 StrategyWorker 类
- 创建一个最小实例，用于调用用户在 BaseStrategyWorker 上重写的钩子方法
- 为 PriceFactorSimulator / CapitalAllocationSimulator 提供统一的钩子调用入口
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import importlib
import inspect
import logging

from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker


logger = logging.getLogger(__name__)


@dataclass
class SimulatorHooksDispatcher:
    """
    模拟器钩子分发器：从 StrategyWorker 中查找并调用钩子。

    使用方式：
        dispatcher = SimulatorHooksDispatcher(strategy_name="example")
        dispatcher.call_hook("on_price_factor_before_process_stock", stock_id, opportunities, config)
    """

    strategy_name: str

    def __post_init__(self) -> None:
        self._worker_class: Optional[type[BaseStrategyWorker]] = None
        self._worker_instance: Optional[BaseStrategyWorker] = None

    # ------------------------------------------------------------------ #
    # 内部：加载用户 StrategyWorker
    # ------------------------------------------------------------------ #

    def _load_worker_class(self) -> Optional[type[BaseStrategyWorker]]:
        """动态加载用户的 StrategyWorker 类。"""
        if self._worker_class is not None:
            return self._worker_class

        module_path = f"app.userspace.strategies.{self.strategy_name}.strategy_worker"
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            logger.warning(
                "[SimulatorHooksDispatcher] 无法加载策略 Worker 模块: %s", module_path
            )
            return None
        except Exception as exc:
            logger.warning(
                "[SimulatorHooksDispatcher] 加载策略 Worker 模块异常: %s, error=%s",
                module_path,
                exc,
            )
            return None

        # 查找继承自 BaseStrategyWorker 的用户类
        for _, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseStrategyWorker)
                and obj is not BaseStrategyWorker
            ):
                self._worker_class = obj
                return self._worker_class

        logger.warning(
            "[SimulatorHooksDispatcher] 在模块 %s 中未找到继承 BaseStrategyWorker 的类",
            module_path,
        )
        return None

    def _get_worker_instance(self) -> Optional[BaseStrategyWorker]:
        """
        获取 Worker 实例（用于调用钩子）。

        说明：
        - 这里构造一个最小的 job_payload，仅供钩子调用使用；
        - 不会在该实例上执行真正的 scan/simulate 流程。
        """
        if self._worker_instance is not None:
            return self._worker_instance

        worker_class = self._load_worker_class()
        if worker_class is None:
            return None

        # 最小化的 payload，避免对现有 Worker 逻辑造成干扰
        dummy_payload: dict[str, Any] = {
            "stock_id": "DUMMY",
            "execution_mode": "scan",
            "strategy_name": self.strategy_name,
            "settings": {},  # 钩子调用场景下不依赖完整 settings
        }

        try:
            self._worker_instance = worker_class(dummy_payload)  # type: ignore[call-arg]
        except Exception as exc:
            logger.warning(
                "[SimulatorHooksDispatcher] 无法创建 StrategyWorker 实例: %s", exc
            )
            self._worker_instance = None

        return self._worker_instance

    # ------------------------------------------------------------------ #
    # 对外：调用钩子
    # ------------------------------------------------------------------ #

    def call_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        调用钩子函数。

        Args:
            hook_name: 钩子方法名（如 'on_price_factor_before_process_stock'）
            *args, **kwargs: 传递给钩子的参数

        Returns:
            钩子函数的返回值；如果钩子不存在或未被用户重写，返回 None。
        """
        instance = self._get_worker_instance()
        if instance is None:
            return None

        hook_method = getattr(instance, hook_name, None)
        if hook_method is None:
            return None

        # 如果方法与基类实现相同，说明用户未重写，直接忽略
        base_method = getattr(BaseStrategyWorker, hook_name, None)
        if base_method is not None and getattr(hook_method, "__func__", None) is base_method:  # type: ignore[attr-defined]
            return None

        try:
            return hook_method(*args, **kwargs)
        except Exception as exc:
            logger.warning(
                "[SimulatorHooksDispatcher] 调用钩子 %s 失败: %s", hook_name, exc
            )
            return None

