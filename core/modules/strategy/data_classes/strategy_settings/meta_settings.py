#!/usr/bin/env python3
"""
设置基类

职责：
- 加载原始 settings 字典（不验证）
- 提供按需验证方法
- 提供公共字段访问
- 添加默认值
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import importlib
import logging

from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult

from core.modules.data_contract.contract_const import DataKey
from core.modules.strategy.models.strategy_settings import StrategySettings as StrategySettingsDictModel

logger = logging.getLogger(__name__)


@dataclass
class BaseSettings(ABC):
    """
    设置基类
    
    职责：
    - 加载原始 settings 字典（不验证）
    - 提供按需验证方法
    - 提供公共字段访问
    - 添加默认值
    """
    
    # 原始配置字典（保留完整原始数据）
    raw_settings: Dict[str, Any]
    
    # 策略基本信息（延迟提取）
    _strategy_name: Optional[str] = None
    _strategy_description: Optional[str] = None
    _is_enabled: Optional[bool] = None
    
    # 验证状态
    _base_validated: bool = False
    
    def __post_init__(self):
        """初始化后不立即验证，只提取基本信息"""
        self._extract_basic_info()
    
    def _extract_basic_info(self) -> None:
        """提取策略基本信息（不验证）"""
        self._strategy_name = self.raw_settings.get("name", "unknown")
        self._strategy_description = self.raw_settings.get("description", "")
        self._is_enabled = bool(self.raw_settings.get("is_enabled", False))
    
    @property
    def strategy_name(self) -> str:
        """获取策略名称"""
        if self._strategy_name is None:
            self._extract_basic_info()
        return self._strategy_name or "unknown"
    
    @property
    def strategy_description(self) -> str:
        """获取策略描述"""
        if self._strategy_description is None:
            self._extract_basic_info()
        return self._strategy_description or ""
    
    @property
    def is_enabled(self) -> bool:
        """是否启用"""
        if self._is_enabled is None:
            self._extract_basic_info()
        return self._is_enabled
    
    @property
    def name(self) -> str:
        """与旧 ``StrategySettings.name`` 对齐。"""
        return self.strategy_name

    def is_valid(self) -> bool:
        """基础校验通过且无 Critical 错误（与组件侧校验迁移后的入口一致）。"""
        result = self.validate_base_settings()
        return bool(result.is_valid) and not result.has_critical_errors()

    @property
    def price_simulator(self) -> Dict[str, Any]:
        p = self.raw_settings.get("price_simulator")
        return p if isinstance(p, dict) else {}

    @property
    def sampling_config(self) -> Dict[str, Any]:
        return self.get_sampling_config()

    @property
    def sampling_amount(self) -> int:
        return self.get_sampling_amount()

    @property
    def max_workers(self) -> Any:
        simulator_cfg = self.price_simulator
        enumerator_cfg = self.raw_settings.get("enumerator") or {}
        performance_cfg = self.raw_settings.get("performance") or {}
        scanner_cfg = self.raw_settings.get("scanner") or {}
        if not isinstance(enumerator_cfg, dict):
            enumerator_cfg = {}
        if not isinstance(performance_cfg, dict):
            performance_cfg = {}
        if not isinstance(scanner_cfg, dict):
            scanner_cfg = {}
        return (
            simulator_cfg.get("max_workers")
            or enumerator_cfg.get("max_workers")
            or performance_cfg.get("max_workers")
            or scanner_cfg.get("max_workers")
            or "auto"
        )

    @property
    def start_date(self) -> str:
        return str(self.price_simulator.get("start_date", "") or "")

    @property
    def end_date(self) -> str:
        return str(self.price_simulator.get("end_date", "") or "")

    def get_scanner_config(self) -> Dict[str, Any]:
        s = self.raw_settings.get("scanner")
        return s if isinstance(s, dict) else {}

    @property
    def watch_list(self) -> Any:
        """``scanner.watch_list``：文件路径（相对策略目录）或内联列表。"""
        return self.get_scanner_config().get("watch_list")

    # =========================================================================
    # 验证方法（按需调用）
    # =========================================================================
    
    def validate_base_settings(self) -> SettingValidationResult:
        """
        验证基础设置（Critical）
        
        验证内容：
        - name 不能为空或 'unknown'（Critical）
        - data.base_required_data（含合法 ``data_id``、可选 ``params``）（Critical）
        
        同时添加默认值：
        - data.min_required_records: 默认 100
        - data.indicators: 默认 {}
        - data.extra_required_data_sources: 默认 []
        - sampling.strategy: 默认 "continuous"
        - sampling.sampling_amount: 默认 10
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 验证 name
        if not self.strategy_name or self.strategy_name == "unknown":
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="name",
                message="策略名称不能为空或 'unknown'",
                suggested_fix='在 settings.py 中添加 "name": "your_strategy_name"'
            ))
            result.is_valid = False
        
        data_config = self.raw_settings.get("data", {})
        try:
            StrategySettingsDictModel.validate_data_config(
                data_config if isinstance(data_config, dict) else {}
            )
        except ValueError as e:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="data.base_required_data",
                message=str(e),
                suggested_fix='在 settings.py 的 data 中配置 '
                '"base_required_data": {"params": {"term": "daily"}} '
                '（data_id 可省略，仅能为 stock.kline；adjust 默认 qfq）',
            ))
            result.is_valid = False

        # 添加默认值（不验证，直接添加）
        self._add_base_default_values()
        
        # 标记已验证
        self._base_validated = True
        
        return result
    
    def _add_base_default_values(self) -> None:
        """添加基础设置的默认值"""
        # 确保 data 存在
        if "data" not in self.raw_settings:
            self.raw_settings["data"] = {}
        
        data_config = self.raw_settings["data"]
        
        # min_required_records 默认值
        if "min_required_records" not in data_config:
            data_config["min_required_records"] = 100
        elif not isinstance(data_config["min_required_records"], int) or data_config["min_required_records"] <= 0:
            data_config["min_required_records"] = 100
        
        # indicators 默认值
        if "indicators" not in data_config:
            data_config["indicators"] = {}
        
        if "extra_required_data_sources" not in data_config:
            data_config["extra_required_data_sources"] = []
        elif not isinstance(data_config["extra_required_data_sources"], list):
            data_config["extra_required_data_sources"] = []

        base = data_config.get("base_required_data")
        if isinstance(base, dict) and base.get("params") is None:
            base["params"] = {}
        
        # sampling 默认值
        if "sampling" not in self.raw_settings:
            self.raw_settings["sampling"] = {}
        
        sampling_config = self.raw_settings["sampling"]
        if "strategy" not in sampling_config:
            sampling_config["strategy"] = "continuous"
        if "sampling_amount" not in sampling_config:
            sampling_config["sampling_amount"] = 10
    
    # =========================================================================
    # 公共字段访问（所有组件都需要）
    # =========================================================================
    
    def get_core_config(self) -> Dict[str, Any]:
        """获取核心配置（策略特定参数）"""
        return self.raw_settings.get("core", {})
    
    def get_data_config(self) -> Dict[str, Any]:
        """获取数据配置"""
        return self.raw_settings.get("data", {})
    
    def get_sampling_config(self) -> Dict[str, Any]:
        """获取采样配置"""
        return self.raw_settings.get("sampling", {})
    
    def get_goal_config(self) -> Dict[str, Any]:
        """获取投资目标配置（止盈止损）"""
        return self.raw_settings.get("goal", {})
    
    def get_fees_config(self) -> Dict[str, Any]:
        """获取交易成本配置"""
        return self.raw_settings.get("fees", {})
    
    # =========================================================================
    # 数据配置便捷访问
    # =========================================================================
    
    def get_base_required_data(self) -> Dict[str, Any]:
        """主数据依赖：``{"data_id": str, "params": dict}``。"""
        data_config = self.get_data_config()
        base = data_config.get("base_required_data")
        return base if isinstance(base, dict) else {}

    def get_extra_required_data_sources(self) -> list:
        data_config = self.get_data_config()
        xs = data_config.get("extra_required_data_sources", [])
        return xs if isinstance(xs, list) else []

    def get_base_data_id(self) -> str:
        """主依赖的 DataKey 字符串（省略 data_id 时为 ``stock.kline``）。"""
        base = self.get_base_required_data()
        if not base:
            return DataKey.STOCK_KLINE.value
        try:
            return StrategySettingsDictModel.normalize_base_required_data(base)["data_id"]
        except ValueError:
            return str(base.get("data_id", "") or "")

    def get_adjust_type(self) -> str:
        """复权类型：具体 K 线 key 由 data_id 推导；``stock.kline`` 由 params.adjust 给出。"""
        from core.modules.strategy.models.strategy_settings import StrategySettings as _StrategySettingsView

        data_cfg = self.get_data_config()
        if not isinstance(data_cfg, dict):
            return "qfq"
        return _StrategySettingsView({"data": data_cfg}).adjust_type
    
    def get_min_required_records(self) -> int:
        """获取最小要求记录数"""
        data_config = self.get_data_config()
        min_records = data_config.get("min_required_records", 100)
        try:
            return max(int(min_records), 1)
        except (TypeError, ValueError):
            return 100
    
    def get_indicators_config(self) -> Dict[str, Any]:
        """获取技术指标配置"""
        data_config = self.get_data_config()
        return data_config.get("indicators", {})
    
    
    # =========================================================================
    # 采样配置便捷访问
    # =========================================================================
    
    def get_sampling_strategy(self) -> str:
        """获取采样策略"""
        sampling_config = self.get_sampling_config()
        return sampling_config.get("strategy", "continuous")
    
    def get_sampling_amount(self) -> int:
        """获取采样数量"""
        sampling_config = self.get_sampling_config()
        amount = sampling_config.get("sampling_amount", 10)
        try:
            return max(int(amount), 1)
        except (TypeError, ValueError):
            return 10
    
    # =========================================================================
    # 工具方法
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（返回原始配置，包含已添加的默认值）"""
        return self.raw_settings
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（直接访问原始配置）"""
        return self.raw_settings.get(key, default)
    
    @classmethod
    def load_from_strategy_name(cls, strategy_name: str) -> 'BaseSettings':
        """
        从策略名称加载设置（不验证）
        
        Args:
            strategy_name: 策略名称（对应 userspace/strategies/{strategy_name}）
        
        Returns:
            BaseSettings 实例（未验证）
        
        Raises:
            ValueError: 如果加载失败
        """
        settings_module_path = f"userspace.strategies.{strategy_name}.settings"
        
        try:
            settings_module = importlib.import_module(settings_module_path)
        except ModuleNotFoundError as e:
            raise ValueError(
                f"[BaseSettings] 无法加载策略 settings: {settings_module_path}"
            ) from e
        
        raw_settings = getattr(settings_module, "settings", None)
        if not isinstance(raw_settings, dict):
            raise ValueError(
                f"[BaseSettings] 策略 {strategy_name} 的 settings.py 中缺少 'settings' 字典"
            )
        
        return cls(raw_settings=raw_settings)
