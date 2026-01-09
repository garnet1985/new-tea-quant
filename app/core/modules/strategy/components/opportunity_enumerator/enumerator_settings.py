#!/usr/bin/env python3
"""
Opportunity Enumerator Settings

职责：
- 从用户的策略 settings 字典中抽取“枚举器真正关心的部分”
- 在枚举开始前做一次集中校验 + 默认值补全

设计约定（与 example/settings.py 对齐）：

settings = {
    "name": "example",
    "description": "...",
    "is_enabled": True/False,
    "core": {...},
    "data": {
        "base": ...,
        "adjust": ...,
        "min_required_records": ...,
        "indicators": {...},
        "required_entities": [...]
    },
    "sampling": {...},
    "simulator": {
        "start_date": "...",
        "end_date": "...",
        "goal": {...}
    },
    "performance": {...}
}
"""

from dataclasses import dataclass, field
from typing import Dict, Any

from app.core.modules.strategy.models.strategy_settings import StrategySettings


@dataclass
class OpportunityEnumeratorSettings:
    """
    枚举器专用的 settings 视图

    - 输入：完整的策略 settings 字典
    - 输出：枚举器真正需要且已经校验/补全过的配置

    使用方式：
        raw_settings = module.settings      # 用户 settings.py 里的字典
        enum_settings = OpportunityEnumeratorSettings.from_raw("example", raw_settings)
        # 之后枚举器可以使用：
        #   enum_settings.min_required_records
        #   enum_settings.goal
        #   enum_settings.data
    """

    strategy_name: str
    raw: Dict[str, Any]

    # 下面字段在 __post_init__ 中由 raw 推导填充
    data: Dict[str, Any] = field(init=False)
    simulator: Dict[str, Any] = field(init=False)
    goal: Dict[str, Any] = field(init=False)

    min_required_records: int = field(init=False)

    def __post_init__(self) -> None:
        """
        在初始化后执行两步：
        1. 检查核心/必要字段是不是齐全有效
        2. 补全缺失的可选字段（写回到内部 data/simulator 视图）
        """
        self._validate_and_normalize()

    # -------------------------------------------------------------------------
    # 工厂方法
    # -------------------------------------------------------------------------
    @classmethod
    def from_raw(cls, strategy_name: str, settings_dict: Dict[str, Any]) -> "OpportunityEnumeratorSettings":
        """
        从完整 settings 字典创建枚举器设置视图
        """
        return cls(strategy_name=strategy_name, raw=settings_dict)

    @classmethod
    def from_base(cls, base_settings: StrategySettings) -> "OpportunityEnumeratorSettings":
        """
        从通用 StrategySettings 创建枚举器设置视图
        （推荐路径：先用 StrategySettings 统一解析，再为各组件各自切视图）
        """
        return cls(strategy_name=base_settings.name, raw=base_settings.to_dict())

    # -------------------------------------------------------------------------
    # 内部校验与补全
    # -------------------------------------------------------------------------
    def _validate_and_normalize(self) -> None:
        """
        1. 检查必要字段：
           - data.base 存在且非空
           - data.adjust 存在且非空
        2. 补全可选字段：
           - data.min_required_records：缺失或非法时使用默认值 100
           - data.indicators：缺失时设为空 dict
           - data.required_entities：缺失时设为空 list
           - simulator.goal：缺失时设为空 dict（允许“无止盈止损”，但建议用户配置）
        """
        settings = self.raw or {}

        # ----- data 部分 -----
        data = dict(settings.get("data") or {})
        base = data.get("base")
        adjust = data.get("adjust")

        if not base:
            raise ValueError(f"[OpportunityEnumeratorSettings] 策略 {self.strategy_name} 的 settings.data.base 不能为空")
        if not adjust:
            raise ValueError(f"[OpportunityEnumeratorSettings] 策略 {self.strategy_name} 的 settings.data.adjust 不能为空")

        # min_required_records：记录数下限（用于预读和游标起点），默认 100
        mrr = data.get("min_required_records", 100)
        try:
            mrr_int = int(mrr)
        except (TypeError, ValueError):
            mrr_int = 100
        if mrr_int <= 0:
            mrr_int = 100
        data["min_required_records"] = mrr_int

        # 其他可选字段
        indicators = data.get("indicators")
        if indicators is None:
            indicators = {}
        data["indicators"] = indicators

        required_entities = data.get("required_entities")
        if required_entities is None:
            required_entities = []
        data["required_entities"] = required_entities

        self.data = data
        self.min_required_records = mrr_int

        # ----- simulator 部分 -----
        simulator = dict(settings.get("simulator") or {})

        goal = simulator.get("goal")
        if goal is None or not goal:
            # ⚠️ 致命错误：枚举器必须配置 goal（止盈止损），否则所有机会都无法完成，会被标记为 expired
            # 如果没有 goal，机会会一直持有直到回测结束，导致 completed_targets 为空
            raise ValueError(
                f"策略 '{self.strategy_name}' 的 settings.simulator.goal 配置缺失或为空！\n"
                f"枚举器需要 goal 配置来定义止盈止损规则，否则所有机会都无法完成。\n"
                f"请在 settings.py 中添加 simulator.goal 配置，例如：\n"
                f"  'simulator': {{\n"
                f"    'goal': {{\n"
                f"      'expiration': {{'fixed_period': 30, 'is_trading_period': True}}\n"
                f"    }}\n"
                f"  }}"
            )
        simulator["goal"] = goal

        self.simulator = simulator
        self.goal = goal

    # -------------------------------------------------------------------------
    # 导出方法
    # -------------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """
        返回一个“已校验 & 补全”的 settings 视图，用于后续 Worker 继续使用。

        策略：
        - 从原始 raw 做一个浅拷贝
        - 用枚举器内部的 data/simulator 视图覆盖对应字段
        - 其他字段（如 core/performance）原样保留，方便其他模块继续使用
        """
        merged = dict(self.raw or {})
        merged["data"] = self.data
        merged["simulator"] = self.simulator
        # goal/min_required_records 已经写回 simulator/data 内部，这里不单独暴露
        return merged

