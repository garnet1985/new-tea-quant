#!/usr/bin/env python3
"""
Opportunity Enumerator Settings

职责：
- 从用户的策略 settings 字典中抽取“枚举器真正关心的部分”
- 在枚举开始前做默认值补全（整包 settings 已在策略发现阶段校验，此处不再重复契约校验）

设计约定（与 example/settings.py 对齐）：

settings = {
    "name": "example",
    "description": "...",
    "is_enabled": True/False,
    "core": {...},
    "data": {
        "base_required_data": {"params": {"term": "daily"}},
        "min_required_records": ...,
        "indicators": {...},
        "extra_required_data_sources": [...]
    },
    "sampling": {...},
    "price_simulator": {
        "start_date": "...",
        "end_date": "...",
        "goal": {...}
    },
    "performance": {...}
}
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Union

from core.modules.strategy.models.strategy_settings import StrategySettings


@dataclass
class OpportunityEnumeratorSettings:
    """
    枚举器专用的 settings 视图

    - 输入：完整的策略 settings 字典
    - 输出：枚举器真正需要且已补全默认值的配置

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
    price_simulator: Dict[str, Any] = field(init=False)
    goal: Dict[str, Any] = field(init=False)
    use_sampling: bool = field(init=False)
    max_workers: "str | int" = field(init=False)
    min_required_records: int = field(init=False)

    # 日志详细程度（控制 worker / scheduler 的自我报告）
    is_verbose: bool = field(init=False)
    
    # Memory-aware batch scheduler 配置（支持 "auto"）
    memory_budget_mb: Union[float, str] = field(init=False)
    warmup_batch_size: Union[int, str] = field(init=False)
    min_batch_size: Union[int, str] = field(init=False)
    max_batch_size: Union[int, str] = field(init=False)
    monitor_interval: int = field(init=False)

    def __post_init__(self) -> None:
        """补全默认值并抽取枚举器视图（不重复校验 data 契约等）。"""
        self._normalize_views()

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
    # 内部：仅补全与视图抽取（契约校验在 ``StrategyDiscoveryHelper.load_strategy``）
    # -------------------------------------------------------------------------
    def _normalize_views(self) -> None:
        """
        补全可选字段（写回到内部 data/price_simulator 视图）：
        - data.min_required_records、indicators、extra_required_data_sources
        - enumerator 各默认
        - goal：来自整包 settings，缺省则为空 dict
        """
        settings = self.raw or {}

        # ----- data 部分 -----
        data = dict(settings.get("data") or {})

        brd = data.get("base_required_data")
        if isinstance(brd, dict) and brd.get("params") is None:
            brd["params"] = {}

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

        extra_sources = data.get("extra_required_data_sources")
        if extra_sources is None:
            extra_sources = []
        data["extra_required_data_sources"] = extra_sources

        self.data = data
        self.min_required_records = mrr_int

        # ----- enumerator 部分 -----
        enumerator = dict(settings.get("enumerator") or {})
        
        # use_sampling：默认 True（使用 sampling 配置进行采样）
        # False 表示使用全量股票列表
        use_sampling = enumerator.get("use_sampling", True)
        if not isinstance(use_sampling, bool):
            use_sampling = True  # 如果不是 bool，默认 True
        self.use_sampling = use_sampling
        
        # max_test_versions：最多保留的测试模式版本数，默认 10
        # 超过此数量的测试版本会被自动清理（删除最早的版本）
        max_test_versions = enumerator.get("max_test_versions", 10)
        try:
            max_test_versions_int = int(max_test_versions)
        except (TypeError, ValueError):
            max_test_versions_int = 10
        if max_test_versions_int < 1:
            max_test_versions_int = 10  # 至少保留 1 个版本
        self.max_test_versions = max_test_versions_int
        
        # max_output_versions：最多保留的全量枚举（output）版本数，默认 3
        # 超过此数量的全量版本会被自动清理（删除最早的版本）
        max_output_versions = enumerator.get("max_output_versions", 3)
        try:
            max_output_versions_int = int(max_output_versions)
        except (TypeError, ValueError):
            max_output_versions_int = 3
        if max_output_versions_int < 1:
            max_output_versions_int = 3  # 至少保留 1 个版本
        self.max_output_versions = max_output_versions_int

        # max_workers：枚举器专用 worker 数量
        max_workers = enumerator.get("max_workers", "auto")
        self.max_workers = max_workers

        # is_verbose：是否输出详细日志（控制 worker / scheduler 自我报告）
        is_verbose = enumerator.get("is_verbose", False)
        self.is_verbose = bool(is_verbose)
        
        # Memory-aware batch scheduler 配置（支持 "auto"）
        memory_budget = enumerator.get("memory_budget_mb", "auto")
        self.memory_budget_mb = memory_budget if memory_budget == "auto" else float(memory_budget)
        
        warmup = enumerator.get("warmup_batch_size", "auto")
        self.warmup_batch_size = warmup if warmup == "auto" else int(warmup)
        
        min_size = enumerator.get("min_batch_size", "auto")
        self.min_batch_size = min_size if min_size == "auto" else int(min_size)
        
        max_size = enumerator.get("max_batch_size", "auto")
        self.max_batch_size = max_size if max_size == "auto" else int(max_size)
        
        self.monitor_interval = int(enumerator.get("monitor_interval", 5))

        # ----- price_simulator 部分 -----
        simulator = dict(settings.get("price_simulator") or {})

        raw_goal = settings.get("goal")
        goal = raw_goal if isinstance(raw_goal, dict) else {}
        self.price_simulator = simulator
        self.goal = goal

    # -------------------------------------------------------------------------
    # 导出方法
    # -------------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """
        返回已补全默认值的 settings 视图，用于后续 Worker 继续使用。

        策略：
        - 从原始 raw 做一个浅拷贝
        - 用枚举器内部的 data/price_simulator 视图覆盖对应字段
        - 其他字段（如 core/performance）原样保留，方便其他模块继续使用
        """
        merged = dict(self.raw or {})
        merged["data"] = self.data
        merged["price_simulator"] = self.price_simulator
        # 确保 enumerator 配置存在
        if "enumerator" not in merged:
            merged["enumerator"] = {}
        merged["enumerator"]["use_sampling"] = self.use_sampling
        merged["enumerator"]["max_test_versions"] = self.max_test_versions
        merged["enumerator"]["max_output_versions"] = self.max_output_versions
        merged["enumerator"]["max_workers"] = self.max_workers
        merged["enumerator"]["is_verbose"] = self.is_verbose
        merged["enumerator"]["memory_budget_mb"] = self.memory_budget_mb
        merged["enumerator"]["warmup_batch_size"] = self.warmup_batch_size
        merged["enumerator"]["min_batch_size"] = self.min_batch_size
        merged["enumerator"]["max_batch_size"] = self.max_batch_size
        merged["enumerator"]["monitor_interval"] = self.monitor_interval
        # goal/min_required_records 已经写回 price_simulator/data 内部，这里不单独暴露
        return merged

