# Strategy 模块架构设计

## 📋 设计目标

从整个 strategy 模块的角度抽象出统一的 Models 和 Managers，实现：
- **职责清晰**：每个 Model/Manager 负责特定功能
- **代码复用**：避免各组件重复实现相同逻辑
- **易于测试**：独立的 Model/Manager 便于单元测试
- **统一接口**：所有组件通过统一的接口交互

## 🏗️ 架构概览

```
strategy/
├── models/              # 领域模型（数据对象）
│   ├── opportunity.py   # 机会对象 ✅
│   ├── investment.py    # 投资对象（新增）
│   ├── account.py       # 账户对象（CA 模拟器）
│   ├── trade.py         # 交易记录对象（CA 模拟器）
│   ├── event.py         # 事件对象（CA 模拟器）
│   ├── result.py        # 结果对象（统一格式）
│   └── performance_metrics.py  # 性能指标对象
│
├── managers/            # 管理器（业务逻辑）
│   ├── strategy_setting_manager.py    # 设置管理器 ✅
│   ├── version_manager.py              # 版本管理器 ✅
│   ├── result_manager.py               # 结果管理器 ✅
│   ├── session_manager.py              # 会话管理器 ✅
│   └── data_loader.py                  # 数据加载器
│
└── components/          # 组件（执行器）
    ├── opportunity_enumerator/
    ├── price_factor_simulator/
    └── capital_allocation_simulator/
```

## 📦 Models 设计

### 1. Opportunity ✅ (已有)

**职责**：表示投资机会

**位置**：`models/opportunity.py`

**状态**：已实现，需要保持兼容

---

### 2. Investment (新增)

**职责**：表示投资记录，由 Opportunity 转化而来

**设计思路**：
- **PriceFactorInvestment**：价格因子模拟器的投资记录（1股，无资金约束）
- **CapitalAllocationInvestment**：资金分配模拟器的投资记录（实际股数，含费用）

**设计**：

```python
# models/investment.py

from abc import ABC
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime

@dataclass
class BaseInvestment(ABC):
    """投资基类"""
    # 基础信息
    investment_id: str
    opportunity_id: str
    stock_id: str
    stock_name: str
    
    # 时间信息
    buy_date: str
    buy_price: float
    sell_date: Optional[str] = None
    sell_price: Optional[float] = None
    
    # 状态
    status: str = 'open'  # open / closed
    
    # 收益信息
    profit: float = 0.0
    roi: float = 0.0
    holding_days: int = 0
    
    @classmethod
    def from_opportunity(cls, opportunity: 'Opportunity') -> 'BaseInvestment':
        """从 Opportunity 创建 Investment"""
        raise NotImplementedError

@dataclass
class PriceFactorInvestment(BaseInvestment):
    """价格因子投资记录（1股，无资金约束）"""
    shares: int = 1  # 固定 1 股
    
    @classmethod
    def from_opportunity(cls, opportunity: 'Opportunity') -> 'PriceFactorInvestment':
        """从 Opportunity 创建 PriceFactorInvestment"""
        return cls(
            investment_id=f"pf_{opportunity.opportunity_id}",
            opportunity_id=opportunity.opportunity_id,
            stock_id=opportunity.stock_id,
            stock_name=opportunity.stock_name,
            buy_date=opportunity.trigger_date,
            buy_price=opportunity.trigger_price,
            sell_date=opportunity.sell_date,
            sell_price=opportunity.sell_price,
            status='closed' if opportunity.sell_date else 'open',
            profit=(opportunity.sell_price - opportunity.trigger_price) if opportunity.sell_price else 0.0,
            roi=opportunity.roi or 0.0,
            holding_days=opportunity.holding_days or 0,
        )

@dataclass
class CapitalAllocationInvestment(BaseInvestment):
    """资金分配投资记录（实际股数，含费用）"""
    shares: int
    avg_cost: float  # 含费用的平均成本
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0
    total_cost: float = 0.0  # 总成本（含费用）
    realized_pnl: float = 0.0  # 已实现盈亏
    
    @classmethod
    def from_trade(cls, buy_trade: 'Trade', sell_trade: Optional['Trade'] = None) -> 'CapitalAllocationInvestment':
        """从交易记录创建 CapitalAllocationInvestment"""
        # 实现逻辑
        pass
```

**使用场景**：
- PriceFactorSimulator：将 Opportunity 转化为 PriceFactorInvestment
- CapitalAllocationSimulator：将 Trade 转化为 CapitalAllocationInvestment
- 结果汇总：统一的 Investment 接口便于统计

---

### 3. Account ✅ (已有，在 CA 模拟器中)

**职责**：管理资金分配模拟器的账户状态

**位置**：`components/capital_allocation_simulator/models.py`

**建议**：移动到 `models/account.py`，使其成为公共模型

**设计**：

```python
# models/account.py

@dataclass
class Account:
    """账户信息"""
    initial_cash: float
    cash: float  # 当前可用现金
    positions: Dict[str, 'Position'] = field(default_factory=dict)
    
    def get_equity(self, stock_prices: Dict[str, float]) -> float:
        """计算总资产"""
        pass
    
    def get_portfolio_size(self) -> int:
        """获取持仓股票数量"""
        pass

@dataclass
class Position:
    """持仓信息"""
    stock_id: str
    shares: int = 0
    avg_cost: float = 0.0
    realized_pnl: float = 0.0
    current_opportunity_id: Optional[str] = None
```

---

### 4. Trade (新增)

**职责**：表示交易记录（买入/卖出）

**设计**：

```python
# models/trade.py

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime

@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    trade_type: Literal['buy', 'sell']
    stock_id: str
    stock_name: str
    date: str
    price: float
    shares: int
    
    # 费用信息
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0
    total_cost: float = 0.0  # 总成本（含费用）
    
    # 关联信息
    opportunity_id: Optional[str] = None
    target_id: Optional[str] = None  # 目标 ID（卖出时）
    
    # 账户状态（交易后）
    cash_after: float = 0.0
    equity_after: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
```

**使用场景**：
- CapitalAllocationSimulator：记录每笔交易
- 结果分析：分析交易频率、成本等

---

### 5. Event (新增)

**职责**：表示事件（触发事件/目标事件）

**设计**：

```python
# models/event.py

from dataclasses import dataclass
from typing import Literal, Dict, Any, Optional

@dataclass
class Event:
    """事件对象"""
    event_type: Literal['trigger', 'target']
    date: str
    stock_id: str
    
    # 事件数据
    opportunity: Optional[Dict[str, Any]] = None  # trigger 事件
    target: Optional[Dict[str, Any]] = None       # target 事件
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'event_type': self.event_type,
            'date': self.date,
            'stock_id': self.stock_id,
            'opportunity': self.opportunity,
            'target': self.target,
        }
```

**使用场景**：
- CapitalAllocationSimulator：构建事件流
- 事件驱动模拟：按时间顺序处理事件

---

### 6. Result (新增)

**职责**：统一的结果对象格式

**设计**：

```python
# models/result.py

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class SimulationResult:
    """模拟结果（统一格式）"""
    # 元信息
    strategy_name: str
    simulator_type: str  # 'price_factor' or 'capital_allocation'
    version_id: str
    created_at: str
    
    # 依赖信息
    sot_version: str
    sot_version_id: str
    
    # 统计信息
    total_stocks: int = 0
    total_opportunities: int = 0
    total_investments: int = 0
    
    # 收益信息
    total_profit: float = 0.0
    total_roi: float = 0.0
    win_rate: float = 0.0
    
    # 详细数据
    investments: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)  # CA 模拟器
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)  # CA 模拟器
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
```

---

### 7. PerformanceMetrics ✅ (已有，在枚举器中)

**职责**：性能指标收集

**位置**：`components/opportunity_enumerator/performance_profiler.py`

**建议**：移动到 `models/performance_metrics.py`，使其成为公共模型

---

## 🎛️ Managers 设计

### 1. StrategySettingManager ✅ (已有，在 setting_management 中)

**职责**：
- 收集整理用户定义的 settings
- 验证 settings 的完整性和可用性
- 分发 settings 给各个执行器

**位置**：`components/setting_management/setting_manager.py`

**设计**：

```python
# managers/strategy_setting_manager.py

class StrategySettingManager:
    """策略设置管理器"""
    
    @staticmethod
    def load_settings(strategy_name: str) -> StrategySettings:
        """加载并验证策略设置"""
        # 1. 加载 settings.py
        # 2. 验证完整性
        # 3. 返回 StrategySettings 对象
        pass
    
    @staticmethod
    def get_enumerator_settings(settings: StrategySettings) -> EnumeratorSettings:
        """获取枚举器设置"""
        pass
    
    @staticmethod
    def get_price_factor_settings(settings: StrategySettings) -> PriceFactorSimulatorConfig:
        """获取价格因子模拟器设置"""
        pass
    
    @staticmethod
    def get_capital_allocation_settings(settings: StrategySettings) -> CapitalAllocationSimulatorConfig:
        """获取资金分配模拟器设置"""
        pass
```

**优势**：
- 统一验证逻辑，避免每个执行器重复验证
- 提供类型安全的配置对象
- 便于配置的版本管理和迁移

---

### 2. VersionManager ✅ (已有，分散在各组件中)

**职责**：
- 管理版本目录（SOT、模拟器版本）
- 创建版本目录
- 解析版本号

**设计**：

```python
# managers/version_manager.py

class VersionManager:
    """版本管理器"""
    
    @staticmethod
    def resolve_sot_version(strategy_name: str, sot_version: str) -> Path:
        """解析 SOT 版本目录"""
        # 统一逻辑，支持 latest、test/latest、具体版本号
        pass
    
    @staticmethod
    def create_enumerator_version(strategy_name: str, is_test: bool = False) -> Tuple[Path, int]:
        """创建枚举器版本目录"""
        pass
    
    @staticmethod
    def create_simulator_version(strategy_name: str, simulator_type: str) -> Tuple[Path, int]:
        """创建模拟器版本目录"""
        # simulator_type: 'price_factor' or 'capital_allocation'
        pass
    
    @staticmethod
    def get_version_metadata(version_dir: Path) -> Dict[str, Any]:
        """获取版本元信息"""
        pass
```

**优势**：
- 统一版本管理逻辑
- 支持版本对比和分析
- 便于版本清理和归档

---

### 3. ResultManager ✅ (已有，分散在各组件中)

**职责**：
- 管理结果目录结构
- 保存结果文件
- 加载历史结果

**设计**：

```python
# managers/result_manager.py

class ResultManager:
    """结果管理器"""
    
    def __init__(self, version_dir: Path):
        self.version_dir = version_dir
    
    def save_opportunities(self, opportunities: List[Opportunity]) -> Path:
        """保存机会 CSV"""
        pass
    
    def save_targets(self, targets: List[Dict]) -> Path:
        """保存目标 CSV"""
        pass
    
    def save_investments(self, investments: List[Investment]) -> Path:
        """保存投资记录"""
        pass
    
    def save_trades(self, trades: List[Trade]) -> Path:
        """保存交易记录"""
        pass
    
    def save_equity_curve(self, equity_curve: List[Dict]) -> Path:
        """保存权益曲线"""
        pass
    
    def save_summary(self, summary: Dict[str, Any]) -> Path:
        """保存汇总结果"""
        pass
    
    def load_opportunities(self) -> List[Dict]:
        """加载机会 CSV"""
        pass
    
    def load_targets(self) -> List[Dict]:
        """加载目标 CSV"""
        pass
```

**优势**：
- 统一文件格式和位置
- 便于结果对比和分析
- 支持结果导出和可视化

---

### 4. SessionManager ✅ (已有)

**职责**：处理会话级别的汇总和统计

**位置**：`components/session_manager.py`

**建议**：移动到 `managers/session_manager.py`

**设计**：

```python
# managers/session_manager.py

class SessionManager:
    """会话管理器"""
    
    @staticmethod
    def aggregate_stock_results(stock_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """聚合股票级别结果"""
        pass
    
    @staticmethod
    def calculate_session_summary(results: Dict[str, Any]) -> Dict[str, Any]:
        """计算会话汇总"""
        pass
    
    @staticmethod
    def build_performance_report(metrics: PerformanceMetrics) -> Dict[str, Any]:
        """构建性能报告"""
        pass
```

---

### 5. DataLoader (新增)

**职责**：统一的数据加载接口

**设计**：

```python
# managers/data_loader.py

class DataLoader:
    """数据加载器"""
    
    @staticmethod
    def load_opportunities(sot_version_dir: Path, stock_id: Optional[str] = None) -> List[Dict]:
        """加载机会数据"""
        pass
    
    @staticmethod
    def load_targets(sot_version_dir: Path, stock_id: Optional[str] = None) -> List[Dict]:
        """加载目标数据"""
        pass
    
    @staticmethod
    def load_opportunities_and_targets(sot_version_dir: Path, stock_id: Optional[str] = None) -> Dict[str, List]:
        """加载机会和目标数据"""
        pass
    
    @staticmethod
    def build_event_stream(sot_version_dir: Path) -> List[Event]:
        """构建事件流"""
        pass
```

**优势**：
- 统一数据加载接口
- 支持缓存和优化
- 便于数据格式迁移

---

## 🔄 组件交互流程

### 枚举器流程

```
OpportunityEnumerator
  ↓
StrategySettingManager.load_settings()
  ↓
VersionManager.create_enumerator_version()
  ↓
BaseStrategyWorker.scan_opportunity()
  ↓
Opportunity (Model)
  ↓
ResultManager.save_opportunities()
```

### 价格因子模拟器流程

```
PriceFactorSimulator
  ↓
StrategySettingManager.get_price_factor_settings()
  ↓
VersionManager.resolve_sot_version()
  ↓
DataLoader.load_opportunities_and_targets()
  ↓
PriceFactorInvestment.from_opportunity()
  ↓
SessionManager.aggregate_stock_results()
  ↓
ResultManager.save_investments()
```

### 资金分配模拟器流程

```
CapitalAllocationSimulator
  ↓
StrategySettingManager.get_capital_allocation_settings()
  ↓
VersionManager.resolve_sot_version()
  ↓
DataLoader.build_event_stream()
  ↓
Event (Model)
  ↓
Account (Model) + Trade (Model)
  ↓
CapitalAllocationInvestment.from_trade()
  ↓
ResultManager.save_trades() + save_equity_curve()
```

---

## 📝 实施计划

### 阶段 1：Models 重构
1. 创建 `models/investment.py`（BaseInvestment, PriceFactorInvestment, CapitalAllocationInvestment）
2. 创建 `models/trade.py`
3. 创建 `models/event.py`
4. 创建 `models/result.py`
5. 移动 `Account` 和 `Position` 到 `models/account.py`
6. 移动 `PerformanceMetrics` 到 `models/performance_metrics.py`

### 阶段 2：Managers 重构
1. 重构 `StrategySettingManager`（统一设置管理）
2. 重构 `VersionManager`（统一版本管理）
3. 重构 `ResultManager`（统一结果管理）
4. 移动 `SessionManager` 到 `managers/`
5. 创建 `DataLoader`（统一数据加载）

### 阶段 3：组件集成
1. 更新 `OpportunityEnumerator` 使用新的 Managers
2. 更新 `PriceFactorSimulator` 使用新的 Models 和 Managers
3. 更新 `CapitalAllocationSimulator` 使用新的 Models 和 Managers

### 阶段 4：测试和文档
1. 编写单元测试
2. 更新文档
3. 编写迁移指南

---

## ✅ 优势总结

1. **职责清晰**：每个 Model/Manager 职责单一，易于理解
2. **代码复用**：公共逻辑统一管理，减少重复
3. **易于测试**：独立的 Model/Manager 便于单元测试
4. **统一接口**：所有组件通过统一的接口交互
5. **易于扩展**：新增功能只需扩展相应的 Model/Manager
6. **类型安全**：使用 dataclass 和类型提示，提高代码质量

---

## 🤔 待讨论问题

1. **Investment 的粒度**：
   - 是否需要区分 PriceFactorInvestment 和 CapitalAllocationInvestment？
   - 还是使用统一的 Investment 基类，通过字段区分？

2. **Result 的格式**：
   - 是否需要统一的 Result 格式？
   - 还是保持各模拟器自己的格式？

3. **Managers 的实例化**：
   - 使用静态方法还是实例方法？
   - 是否需要单例模式？

4. **数据加载缓存**：
   - DataLoader 是否需要缓存机制？
   - 如何避免重复加载？
