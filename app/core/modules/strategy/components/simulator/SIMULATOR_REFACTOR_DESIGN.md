# Simulator 重构设计方案

## 📋 目标

1. **整理两个模拟器**：PriceFactorSimulator 和 CapitalAllocationSimulator
2. **抽取公共部分**：统一版本管理、设置加载、采样处理等
3. **重新组织文件夹结构**：更清晰的模块划分
4. **暴露钩子函数**：让用户可以复写关键逻辑

## 🔍 现状分析

### 共同点

1. **设置加载**：都需要加载策略 settings，解析配置
2. **版本管理**：都需要解析 SOT 版本目录，创建模拟器版本目录
3. **采样处理**：都需要根据 `use_sampling` 配置过滤股票
4. **辅助工具**：都有 `DateTimeEncoder`（完全相同）
5. **结果保存**：都需要保存结果到版本目录
6. **数据加载**：都需要从 SOT 目录加载机会和目标数据

### 差异点

| 特性 | PriceFactorSimulator | CapitalAllocationSimulator |
|------|---------------------|---------------------------|
| 执行模式 | 多进程（ProcessWorker） | 单进程 |
| 数据粒度 | 每只股票独立 | 全局账户统一 |
| 资金管理 | 无（1股入场） | 有（Account + Position） |
| 数据加载 | OpportunityLoader | EventBuilder |
| 输出格式 | 每股票 JSON + session summary | 交易记录 + 权益曲线 + 汇总 |
| Worker | PriceFactorSimulatorWorker | 无 |

## 🏗️ 重构方案

### 1. 新的文件夹结构

```
app/core/modules/strategy/components/simulator/
├── __init__.py
├── base/
│   ├── __init__.py
│   ├── base_simulator.py          # 基类，包含公共逻辑
│   ├── base_simulator_config.py   # 基础配置类
│   └── simulator_hooks_dispatcher.py  # 钩子分发器（从 StrategyWorker 中调用钩子）
├── common/
│   ├── __init__.py
│   ├── version_manager.py         # 统一版本管理
│   ├── settings_loader.py         # 统一设置加载
│   ├── sampling_filter.py        # 统一采样过滤
│   └── helpers.py                 # 公共辅助函数（DateTimeEncoder等）
├── price_factor/
│   ├── __init__.py
│   ├── price_factor_simulator.py  # PriceFactorSimulator（继承BaseSimulator）
│   ├── price_factor_worker.py     # PriceFactorSimulatorWorker
│   ├── price_factor_config.py     # PriceFactorSimulatorConfig
│   ├── opportunity_loader.py       # 机会加载器
│   ├── investment_builder.py      # 投资记录构建器
│   ├── stock_summary_builder.py   # 股票汇总构建器
│   ├── result_aggregator.py       # 结果聚合器
│   └── result_presenter.py        # 结果展示器
├── capital_allocation/
│   ├── __init__.py
│   ├── capital_allocation_simulator.py  # CapitalAllocationSimulator（继承BaseSimulator）
│   ├── capital_allocation_config.py      # CapitalAllocationSimulatorConfig
│   ├── models.py                  # Account, Position
│   ├── fee_calculator.py          # 费用计算器
│   ├── allocation_strategy.py      # 分配策略
│   ├── event_builder.py           # 事件构建器
│   └── event_handler.py           # 事件处理器（从simulator中提取）
└── README.md
```

### 2. BaseSimulator 基类设计

```python
class BaseSimulator(ABC):
    """模拟器基类，包含公共逻辑"""
    
    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose
        self.hooks = self._init_hooks()  # 初始化钩子
    
    def run(self, strategy_name: str) -> Dict[str, Any]:
        """主执行流程（模板方法模式）"""
        # 1. 加载设置
        settings = self._load_settings(strategy_name)
        config = self._build_config(settings)
        
        # 2. 解析 SOT 版本
        sot_version_dir = self._resolve_sot_version(strategy_name, config.sot_version)
        
        # 3. 创建模拟器版本目录
        sim_version_dir = self._create_simulation_version_dir(strategy_name)
        
        # 4. 加载数据
        data = self._load_data(sot_version_dir, config)
        
        # 5. 应用采样过滤
        if config.use_sampling:
            data = self._apply_sampling(data, settings)
        
        # 6. 执行模拟（子类实现）
        results = self._execute_simulation(data, config, sim_version_dir)
        
        # 7. 保存结果（子类实现）
        self._save_results(results, sim_version_dir, config)
        
        # 8. 返回摘要
        return self._build_summary(results, config)
    
    # 钩子函数（子类可复写）
    def _load_data(self, sot_version_dir: Path, config) -> Any:
        """加载数据（钩子）"""
        pass
    
    def _execute_simulation(self, data: Any, config, sim_version_dir: Path) -> Dict[str, Any]:
        """执行模拟（子类必须实现）"""
        raise NotImplementedError
    
    def _save_results(self, results: Dict[str, Any], sim_version_dir: Path, config) -> None:
        """保存结果（子类必须实现）"""
        raise NotImplementedError
    
    def _build_summary(self, results: Dict[str, Any], config) -> Dict[str, Any]:
        """构建摘要（钩子）"""
        return {}
    
    # 公共方法（使用 common 模块）
    def _load_settings(self, strategy_name: str) -> StrategySettings:
        """加载策略设置"""
        from .common.settings_loader import load_strategy_settings
        return load_strategy_settings(strategy_name)
    
    def _resolve_sot_version(self, strategy_name: str, sot_version: str) -> Path:
        """解析 SOT 版本目录"""
        from .common.version_manager import resolve_sot_version_dir
        return resolve_sot_version_dir(strategy_name, sot_version)
    
    def _create_simulation_version_dir(self, strategy_name: str) -> Path:
        """创建模拟器版本目录"""
        from .common.version_manager import create_simulation_version_dir
        return create_simulation_version_dir(strategy_name, self.get_simulator_type())
    
    def _apply_sampling(self, data: Any, settings: StrategySettings) -> Any:
        """应用采样过滤"""
        from .common.sampling_filter import apply_sampling_to_data
        return apply_sampling_to_data(data, settings)
    
    def _init_hooks_dispatcher(self, strategy_name: str):
        """初始化钩子分发器"""
        from .base.simulator_hooks_dispatcher import SimulatorHooksDispatcher
        return SimulatorHooksDispatcher(strategy_name)
    
    @abstractmethod
    def get_simulator_type(self) -> str:
        """返回模拟器类型（用于版本目录路径）"""
        pass
```

### 3. 钩子函数设计

```python
# base/hooks.py

from typing import Protocol, Any, Dict, List
from pathlib import Path

class SimulatorHooks(Protocol):
    """模拟器钩子函数接口"""
    
    def before_load_data(self, sot_version_dir: Path, config: Any) -> None:
        """数据加载前钩子"""
        pass
    
    def after_load_data(self, data: Any, config: Any) -> Any:
        """数据加载后钩子（可修改数据）"""
        return data
    
    def before_simulation(self, data: Any, config: Any) -> None:
        """模拟开始前钩子"""
        pass
    
    def after_simulation(self, results: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """模拟结束后钩子（可修改结果）"""
        return results
    
    def before_save_results(self, results: Dict[str, Any], sim_version_dir: Path) -> None:
        """保存结果前钩子"""
        pass
    
    def after_save_results(self, sim_version_dir: Path, summary: Dict[str, Any]) -> None:
        """保存结果后钩子"""
        pass

# PriceFactorSimulator 特定钩子
class PriceFactorHooks(SimulatorHooks):
    """PriceFactorSimulator 钩子函数"""
    
    def before_process_stock(self, stock_id: str, opportunities: List[Dict], config: Any) -> None:
        """处理单只股票前钩子"""
        pass
    
    def after_process_stock(self, stock_id: str, stock_summary: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """处理单只股票后钩子（可修改股票汇总）"""
        return stock_summary
    
    def on_opportunity_trigger(self, opportunity: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """机会触发时钩子（可修改机会数据）"""
        return opportunity
    
    def on_target_hit(self, target: Dict[str, Any], opportunity: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """目标命中时钩子（可修改目标数据）"""
        return target

# CapitalAllocationSimulator 特定钩子
class CapitalAllocationHooks(SimulatorHooks):
    """CapitalAllocationSimulator 钩子函数"""
    
    def before_trigger_event(self, event: Dict[str, Any], account: Account, config: Any) -> Dict[str, Any]:
        """触发事件处理前钩子（可修改事件）"""
        return event
    
    def after_trigger_event(self, event: Dict[str, Any], trade: Dict[str, Any], account: Account, config: Any) -> Dict[str, Any]:
        """触发事件处理后钩子（可修改交易记录）"""
        return trade
    
    def before_target_event(self, event: Dict[str, Any], account: Account, config: Any) -> Dict[str, Any]:
        """目标事件处理前钩子（可修改事件）"""
        return event
    
    def after_target_event(self, event: Dict[str, Any], trade: Dict[str, Any], account: Account, config: Any) -> Dict[str, Any]:
        """目标事件处理后钩子（可修改交易记录）"""
        return trade
    
    def calculate_shares_to_buy(self, event: Dict[str, Any], account: Account, config: Any) -> int:
        """计算买入股数钩子（可自定义分配逻辑）"""
        # 默认返回 -1，表示使用默认策略
        return -1
    
    def calculate_shares_to_sell(self, event: Dict[str, Any], position: Position, config: Any) -> int:
        """计算卖出股数钩子（可自定义卖出逻辑）"""
        # 默认返回 -1，表示使用默认策略
        return -1
```

### 4. Common 模块设计

#### version_manager.py
```python
"""统一版本管理器"""

def create_simulation_version_dir(strategy_name: str, simulator_type: str) -> Tuple[Path, int]:
    """
    创建模拟器版本目录
    
    Args:
        strategy_name: 策略名称
        simulator_type: 模拟器类型（"price_factor" 或 "capital_allocation"）
    """
    # 统一的版本目录创建逻辑
    pass

def resolve_sot_version_dir(strategy_name: str, sot_version: str) -> Tuple[Path, Path]:
    """解析 SOT 版本目录（统一逻辑）"""
    # 合并两个模拟器的版本解析逻辑
    pass
```

#### settings_loader.py
```python
"""统一设置加载器"""

def load_strategy_settings(strategy_name: str) -> StrategySettings:
    """加载策略设置（统一逻辑）"""
    # 从两个模拟器中提取公共逻辑
    pass
```

#### sampling_filter.py
```python
"""统一采样过滤器"""

def apply_sampling_to_data(data: Any, settings: StrategySettings) -> Any:
    """应用采样过滤到数据"""
    # 统一的采样逻辑
    pass
```

### 5. 子类实现示例

#### PriceFactorSimulator
```python
class PriceFactorSimulator(BaseSimulator):
    """价格因子模拟器"""
    
    def get_simulator_type(self) -> str:
        return "price_factor"
    
    def _load_data(self, sot_version_dir: Path, config: PriceFactorSimulatorConfig) -> Dict[str, List]:
        """加载机会和目标数据"""
        from .price_factor.opportunity_loader import OpportunityLoader
        loader = OpportunityLoader()
        return loader.load_opportunities_and_targets(sot_version_dir, config)
    
    def _execute_simulation(self, data: Dict[str, List], config, sim_version_dir: Path) -> Dict[str, Any]:
        """执行多进程模拟"""
        # 调用 ProcessWorker，使用 PriceFactorSimulatorWorker
        pass
    
    def _save_results(self, results: Dict[str, Any], sim_version_dir: Path, config) -> None:
        """保存结果"""
        # 保存每只股票的 JSON 和 session summary
        pass
```

#### CapitalAllocationSimulator
```python
class CapitalAllocationSimulator(BaseSimulator):
    """资金分配模拟器"""
    
    def get_simulator_type(self) -> str:
        return "capital_allocation"
    
    def _load_data(self, sot_version_dir: Path, config: CapitalAllocationSimulatorConfig) -> List[Dict]:
        """构建事件流"""
        from .capital_allocation.event_builder import EventBuilder
        return EventBuilder.build_event_stream(sot_version_dir)
    
    def _execute_simulation(self, events: List[Dict], config, sim_version_dir: Path) -> Dict[str, Any]:
        """执行单进程模拟"""
        # 初始化账户、策略等
        # 处理事件流
        # 返回结果
        pass
    
    def _save_results(self, results: Dict[str, Any], sim_version_dir: Path, config) -> None:
        """保存结果"""
        # 保存交易记录、权益曲线、汇总结果
        pass
```

## 🎣 钩子函数设计（与 BaseStrategyWorker 集成）

### 核心思想

**让模拟器钩子函数直接在 `BaseStrategyWorker` 中定义**，这样用户就不需要创建额外的文件。所有策略相关的逻辑（枚举、模拟器钩子）都在同一个类中。

### 钩子函数在 BaseStrategyWorker 中的定义

```python
# app/core/modules/strategy/base_strategy_worker.py

class BaseStrategyWorker(ABC):
    """策略 Worker 基类"""
    
    # =========================================================================
    # 现有钩子（枚举器相关）
    # =========================================================================
    
    def on_init(self):
        """初始化钩子（可选重写）"""
        pass
    
    def on_before_scan(self):
        """扫描前钩子（可选重写）"""
        pass
    
    def on_after_scan(self, opportunity: Optional['Opportunity']):
        """扫描后钩子（可选重写）"""
        pass
    
    def on_before_simulate(self, opportunity: 'Opportunity'):
        """模拟前钩子（可选重写）"""
        pass
    
    def on_after_simulate(self, opportunity: 'Opportunity'):
        """模拟后钩子（可选重写）"""
        pass
    
    # =========================================================================
    # 新增钩子（PriceFactorSimulator 相关）
    # =========================================================================
    
    def on_price_factor_before_process_stock(self, stock_id: str, opportunities: List[Dict], config: Any) -> None:
        """价格因子模拟：处理单只股票前钩子（可选重写）"""
        pass
    
    def on_price_factor_after_process_stock(self, stock_id: str, stock_summary: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """价格因子模拟：处理单只股票后钩子（可选重写，可修改股票汇总）"""
        return stock_summary
    
    def on_price_factor_opportunity_trigger(self, opportunity: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """价格因子模拟：机会触发时钩子（可选重写，可修改机会数据）"""
        return opportunity
    
    def on_price_factor_target_hit(self, target: Dict[str, Any], opportunity: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """价格因子模拟：目标命中时钩子（可选重写，可修改目标数据）"""
        return target
    
    # =========================================================================
    # 新增钩子（CapitalAllocationSimulator 相关）
    # =========================================================================
    
    def on_capital_allocation_before_trigger_event(self, event: Dict[str, Any], account: 'Account', config: Any) -> Dict[str, Any]:
        """资金分配模拟：触发事件处理前钩子（可选重写，可修改事件）"""
        return event
    
    def on_capital_allocation_after_trigger_event(self, event: Dict[str, Any], trade: Dict[str, Any], account: 'Account', config: Any) -> Dict[str, Any]:
        """资金分配模拟：触发事件处理后钩子（可选重写，可修改交易记录）"""
        return trade
    
    def on_capital_allocation_before_target_event(self, event: Dict[str, Any], account: 'Account', config: Any) -> Dict[str, Any]:
        """资金分配模拟：目标事件处理前钩子（可选重写，可修改事件）"""
        return event
    
    def on_capital_allocation_after_target_event(self, event: Dict[str, Any], trade: Dict[str, Any], account: 'Account', config: Any) -> Dict[str, Any]:
        """资金分配模拟：目标事件处理后钩子（可选重写，可修改交易记录）"""
        return trade
    
    def on_capital_allocation_calculate_shares_to_buy(self, event: Dict[str, Any], account: 'Account', config: Any, default_shares: int) -> Optional[int]:
        """
        资金分配模拟：计算买入股数钩子（可选重写，可自定义分配逻辑）
        
        Args:
            event: 触发事件
            account: 账户对象
            config: 模拟器配置
            default_shares: 默认策略计算的股数
        
        Returns:
            int: 自定义买入股数（如果返回 None，则使用 default_shares）
        """
        return None  # 返回 None 表示使用默认策略
    
    def on_capital_allocation_calculate_shares_to_sell(self, event: Dict[str, Any], position: 'Position', config: Any, default_shares: int) -> Optional[int]:
        """
        资金分配模拟：计算卖出股数钩子（可选重写，可自定义卖出逻辑）
        
        Args:
            event: 目标事件
            position: 持仓对象
            config: 模拟器配置
            default_shares: 默认策略计算的股数
        
        Returns:
            int: 自定义卖出股数（如果返回 None，则使用 default_shares）
        """
        return None  # 返回 None 表示使用默认策略
```

### 钩子发现和调用机制

模拟器需要能够找到并调用用户的 `StrategyWorker` 类中的钩子方法：

```python
# app/core/modules/strategy/components/simulator/base/simulator_hooks_dispatcher.py

class SimulatorHooksDispatcher:
    """模拟器钩子分发器：从 StrategyWorker 中查找并调用钩子"""
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self._worker_class = None
        self._worker_instance = None
    
    def _load_worker_class(self):
        """动态加载用户的 StrategyWorker 类"""
        if self._worker_class is not None:
            return self._worker_class
        
        import importlib
        import inspect
        from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
        
        module_path = f"app.userspace.strategies.{self.strategy_name}.strategy_worker"
        try:
            module = importlib.import_module(module_path)
            
            # 查找继承自 BaseStrategyWorker 的类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseStrategyWorker) and 
                    obj != BaseStrategyWorker):
                    self._worker_class = obj
                    return self._worker_class
            
            raise ValueError(f"找不到策略 Worker 类: {module_path}")
        except Exception as e:
            logger.warning(f"无法加载 StrategyWorker 类: {e}")
            self._worker_class = None
            return None
    
    def _get_worker_instance(self):
        """获取 Worker 实例（用于调用钩子）"""
        if self._worker_instance is not None:
            return self._worker_instance
        
        worker_class = self._load_worker_class()
        if worker_class is None:
            return None
        
        # 创建一个最小化的 job_payload（仅用于钩子调用，不执行实际逻辑）
        dummy_payload = {
            'stock_id': 'DUMMY',
            'execution_mode': 'scan',
            'strategy_name': self.strategy_name,
            'settings': {}  # 钩子调用时不需要完整 settings
        }
        
        try:
            self._worker_instance = worker_class(dummy_payload)
        except Exception as e:
            logger.warning(f"无法创建 Worker 实例: {e}")
            return None
        
        return self._worker_instance
    
    def call_hook(self, hook_name: str, *args, **kwargs):
        """
        调用钩子函数
        
        Args:
            hook_name: 钩子方法名（如 'on_price_factor_before_process_stock'）
            *args, **kwargs: 传递给钩子的参数
        
        Returns:
            钩子函数的返回值，如果钩子不存在则返回 None
        """
        instance = self._get_worker_instance()
        if instance is None:
            return None
        
        hook_method = getattr(instance, hook_name, None)
        if hook_method is None:
            return None
        
        # 检查是否是用户重写的方法（不是基类的默认实现）
        if hook_method.__func__ is getattr(BaseStrategyWorker, hook_name, None):
            # 用户没有重写，返回 None
            return None
        
        try:
            return hook_method(*args, **kwargs)
        except Exception as e:
            logger.warning(f"调用钩子 {hook_name} 失败: {e}")
            return None
```

### 在模拟器中使用钩子

```python
# app/core/modules/strategy/components/simulator/capital_allocation/capital_allocation_simulator.py

class CapitalAllocationSimulator(BaseSimulator):
    """资金分配模拟器"""
    
    def __init__(self, is_verbose: bool = False):
        super().__init__(is_verbose)
        self.hooks_dispatcher = None
    
    def run(self, strategy_name: str) -> Dict[str, Any]:
        """运行模拟器"""
        # 初始化钩子分发器
        self.hooks_dispatcher = SimulatorHooksDispatcher(strategy_name)
        
        # ... 其他逻辑
        
        # 在适当的地方调用钩子
        for event in events:
            if event_type == "trigger":
                # 调用钩子：处理前
                modified_event = self.hooks_dispatcher.call_hook(
                    'on_capital_allocation_before_trigger_event',
                    event, account, config
                ) or event
                
                # 执行买入逻辑
                trade = self._handle_trigger_event(modified_event, account, ...)
                
                # 调用钩子：计算买入股数（如果用户自定义）
                custom_shares = self.hooks_dispatcher.call_hook(
                    'on_capital_allocation_calculate_shares_to_buy',
                    event, account, config, trade.get('shares', 0)
                )
                if custom_shares is not None:
                    trade['shares'] = custom_shares
                    # 重新计算交易金额等
                
                # 调用钩子：处理后
                trade = self.hooks_dispatcher.call_hook(
                    'on_capital_allocation_after_trigger_event',
                    event, trade, account, config
                ) or trade
```

### 用户使用示例

```python
# app/userspace/strategies/example/strategy_worker.py

from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from app.core.modules.strategy.models.opportunity import Opportunity
from typing import Optional, Dict, Any

class ExampleStrategyWorker(BaseStrategyWorker):
    """示例策略 Worker"""
    
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]:
        """扫描投资机会（枚举器使用）"""
        # ... 原有逻辑
        pass
    
    # =========================================================================
    # 模拟器钩子（可选实现）
    # =========================================================================
    
    def on_capital_allocation_calculate_shares_to_buy(
        self, 
        event: Dict[str, Any], 
        account: 'Account', 
        config: Any, 
        default_shares: int
    ) -> Optional[int]:
        """
        自定义买入逻辑：根据信号强度调整买入量
        
        例如：如果机会的 extra_fields 中有 signal_strength，则按比例调整
        """
        opportunity = event.get("opportunity", {})
        signal_strength = opportunity.get("extra_fields", {}).get("signal_strength", 1.0)
        
        if signal_strength > 1.5:
            # 强信号，增加 50% 买入量
            return int(default_shares * 1.5)
        elif signal_strength < 0.5:
            # 弱信号，减少 50% 买入量
            return int(default_shares * 0.5)
        
        # 返回 None 表示使用默认策略
        return None
    
    def on_capital_allocation_after_trigger_event(
        self, 
        event: Dict[str, Any], 
        trade: Dict[str, Any], 
        account: 'Account', 
        config: Any
    ) -> Dict[str, Any]:
        """交易后记录额外信息"""
        # 添加自定义指标
        trade["custom_metric"] = self._calculate_custom_metric(event, account)
        trade["signal_quality"] = event.get("opportunity", {}).get("extra_fields", {}).get("rsi_value", 0)
        return trade
    
    def on_price_factor_opportunity_trigger(
        self, 
        opportunity: Dict[str, Any], 
        config: Any
    ) -> Dict[str, Any]:
        """价格因子模拟：机会触发时添加额外信息"""
        # 可以修改机会数据，例如添加标签
        opportunity["custom_tag"] = "high_confidence"
        return opportunity
```

### 优势

1. **统一入口**：所有策略逻辑（枚举 + 模拟器钩子）都在 `StrategyWorker` 中
2. **无需额外文件**：用户不需要创建 `simulator_hooks.py`
3. **类型安全**：钩子方法有明确的签名和文档
4. **可选实现**：用户只需要实现需要的钩子，其他使用默认行为
5. **易于发现**：IDE 可以自动补全钩子方法名
6. **向后兼容**：不实现钩子时，模拟器使用默认行为

### 钩子方法命名规范

为了清晰区分不同模拟器的钩子，使用前缀：
- `on_price_factor_*` - PriceFactorSimulator 钩子
- `on_capital_allocation_*` - CapitalAllocationSimulator 钩子

这样用户可以一目了然地知道哪些钩子属于哪个模拟器。

## 📝 迁移计划

### 阶段 1：创建新结构
1. 创建 `simulator/` 目录结构
2. 创建 `base/`、`common/` 目录
3. 移动现有代码到新位置

### 阶段 2：抽取公共逻辑
1. 实现 `BaseSimulator` 基类
2. 实现 `common/` 模块（version_manager, settings_loader, sampling_filter, helpers）
3. 统一版本管理逻辑

### 阶段 3：重构子类
1. 重构 `PriceFactorSimulator` 继承 `BaseSimulator`
2. 重构 `CapitalAllocationSimulator` 继承 `BaseSimulator`
3. 提取事件处理逻辑到 `event_handler.py`

### 阶段 4：实现钩子系统
1. 在 `BaseStrategyWorker` 中添加模拟器钩子方法定义
2. 实现 `SimulatorHooksDispatcher` 钩子分发器
3. 在模拟器中集成钩子调用点
4. 编写使用示例和文档

### 阶段 5：测试和文档
1. 测试两个模拟器的功能
2. 更新文档
3. 编写钩子函数使用指南

## ✅ 优势

1. **代码复用**：公共逻辑统一管理，减少重复
2. **易于扩展**：新增模拟器只需继承 `BaseSimulator`
3. **灵活定制**：通过钩子函数允许用户自定义逻辑
4. **清晰结构**：模块职责明确，易于维护
5. **向后兼容**：保持现有 API 不变，内部重构

## 🤔 待讨论问题

1. **钩子函数的注册方式**：✅ **已确定**
   - **方案**：直接在 `BaseStrategyWorker` 中定义钩子方法
   - **优势**：统一入口，无需额外文件，易于发现和使用
   - **实现**：通过 `SimulatorHooksDispatcher` 动态加载和调用

2. **版本目录路径**：
   - 当前：`results/simulations/price_factor/` 和 `results/capital_allocation/`
   - 是否统一为：`results/simulations/{simulator_type}/`？
   - **建议**：保持当前路径，更清晰明确

3. **Worker 类的处理**：
   - PriceFactorSimulatorWorker 是否也需要重构？
   - 是否抽取 BaseSimulatorWorker？
   - **建议**：PriceFactorSimulatorWorker 可以保持独立，因为它主要是多进程 Worker，与 BaseStrategyWorker 职责不同

4. **配置类的继承关系**：
   - 是否创建 BaseSimulatorConfig？
   - 如何统一配置加载逻辑？
   - **建议**：创建 `BaseSimulatorConfig`，包含公共字段（sot_version, use_sampling 等）

## 📌 下一步

1. 讨论并确定钩子函数的注册方式
2. 确定版本目录路径规范
3. 开始实施阶段 1 和阶段 2
