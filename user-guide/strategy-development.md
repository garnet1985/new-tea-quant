# 策略开发指南

本指南帮助您基于 New Tea Quant 框架开发自定义量化策略。

## 快速开始

### 1. 创建策略目录

在 `userspace/strategies/` 下创建您的策略目录：

```bash
mkdir -p userspace/strategies/my_strategy
cd userspace/strategies/my_strategy
```

### 2. 创建策略 Worker

创建 `strategy_worker.py`，继承 `BaseStrategyWorker`：

```python
from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.models.opportunity import Opportunity

class MyStrategyWorker(BaseStrategyWorker):
    """我的自定义策略"""
    
    def scan_opportunity(self, stock_id: str, date: str) -> Opportunity:
        """扫描投资机会"""
        # 实现您的策略逻辑
        # 返回 Opportunity 对象或 None
        pass
    
    def simulate_opportunity(self, opportunity: Opportunity) -> dict:
        """模拟投资机会"""
        # 实现回测逻辑
        # 返回模拟结果字典
        pass
```

### 3. 创建策略配置

创建 `settings.py`，定义策略配置：

```python
from core.modules.strategy.components.setting_management.strategy_settings import BaseStrategySettings

class MyStrategySettings(BaseStrategySettings):
    """策略配置"""
    
    name = "my_strategy"
    
    data = {
        "base_price_source": "stock_kline_daily",
        "adjust_type": "qfq"
    }
    
    goal = {
        "expiration": {
            "fixed_window_in_days": 30
        }
    }
```

### 4. 运行策略

```bash
# 机会枚举
python start.py enumerate --strategy my_strategy

# 价格因子模拟
python start.py price_factor --strategy my_strategy

# 资金分配模拟
python start.py capital_allocation --strategy my_strategy
```

## 核心概念

### Opportunity（投资机会）

`Opportunity` 是策略识别的投资机会，包含：

- `stock_id`: 股票代码
- `entry_date`: 入场日期
- `entry_price`: 入场价格
- `target_price`: 目标价格（可选）
- `stop_loss_price`: 止损价格（可选）

### 策略生命周期

1. **扫描阶段** (`scan_opportunity`): 识别投资机会
2. **枚举阶段**: 批量扫描全市场，生成机会列表
3. **模拟阶段** (`simulate_opportunity`): 回测每个机会
4. **分析阶段**: 分析回测结果，评估策略表现

## 详细文档

- [Strategy 框架架构](../docs/architecture/strategy_architecture.md) - 深入了解策略框架设计
- [示例策略](../../userspace/strategies/example/) - 完整示例代码
- [Strategy README](../../core/modules/strategy/README.md) - 策略模块详细文档

## 相关文档

- [数据源使用指南](data-source-usage.md) - 如何获取数据
- [标签系统指南](tag-system.md) - 如何使用标签数据
- [架构文档](../docs/architecture/) - 系统架构文档
