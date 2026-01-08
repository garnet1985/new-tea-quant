# Opportunity Enumerator

## 概述

OpportunityEnumerator 是一个**机会枚举器**，负责**完整枚举**策略的所有投资机会。

### 核心特点

- ✅ **完整枚举**：每天都扫描，不跳过任何可能的机会
- ✅ **同时追踪多个机会**：即使已有持仓也继续查找新机会
- ✅ **完整记录**：每个机会独立追踪，记录 `completed_targets`
- ✅ **使用 Opportunity 实例方法**：`check_targets()`, `settle()`
- ✅ **CSV 存储**：高性能，Excel 可直接打开
- ✅ **每次重新计算**：保证结果反映最新策略代码
- ✅ **多进程并行**：高效处理大量股票

---

## 使用方法

```python
from app.core.modules.strategy.components.opportunity_enumerator import OpportunityEnumerator

# 方式 1：自动计算 worker 数量（推荐）⭐
all_opportunities = OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20231231',
    stock_list=['000001.SZ', '000002.SZ', ...],
    max_workers='auto'  # ✅ 自动计算（根据任务类型和 CPU 核心数）
)

# 方式 2：手动指定 worker 数量
all_opportunities = OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20231231',
    stock_list=['000001.SZ', '000002.SZ', ...],
    max_workers=10  # ✅ 手动指定（会自动保护，最多 2 倍 CPU 核心数）
)

print(f"找到 {len(all_opportunities)} 个机会")
```

---

## 与 Simulator 的区别

| 特性 | Simulator | OpportunityEnumerator |
|------|-----------|----------------------|
| **持仓限制** | 同时只能持有 1 个 | 同时追踪多个（可重叠） |
| **扫描频率** | 无持仓时才扫描 | 每天都扫描（完整枚举） |
| **输出** | 主线机会（一条路径） | 所有可能机会（多条路径） |
| **用途** | 策略验证（主线回测） | 完整枚举（供 Allocation 使用） |
| **输出格式** | JSON | CSV 双表 |

### 示例对比

```
Simulator（主线，单一路径）：
1月1日：发现机会A，买入
1月2日：持有A（❌ 不扫描）
1月3日：持有A（❌ 不扫描）
1月5日：A完成（止盈）
1月6日：发现机会D，买入
...

Enumerator（完整枚举，所有路径）：
1月1日：发现机会A，开始追踪
1月2日：继续追踪A + ✅ 发现机会B，开始追踪B
1月3日：继续追踪A和B + ✅ 发现机会C，开始追踪C
1月5日：A完成（止盈） + 继续追踪B和C
1月9日：C完成（止损） + 继续追踪B
...
```

**关键区别**：
- Simulator：模拟实际交易（一次只买一个）
- Enumerator：枚举所有可能（同时追踪多个）

---

## 输出结构

### 文件结构

```
results/opportunity_enumerator/
└── momentum/                    # 策略名称
    └── 20230101_20231231/      # 时间范围
        ├── opportunities.csv   # 主表
        ├── targets.csv         # 子表（completed_targets）
        └── metadata.json       # 元信息
```

**说明**：
- 每次运行**覆盖**同时间范围的结果
- 保证结果始终反映最新策略代码
- CSV 文件可用 Excel 直接打开

### opportunities.csv

```csv
opportunity_id,stock_id,trigger_date,trigger_price,status,roi
uuid-1,000001.SZ,20230115,10.50,completed,0.067
uuid-2,000001.SZ,20230116,10.55,completed,-0.023
uuid-3,000002.SZ,20230115,8.20,completed,0.105
```

### targets.csv

```csv
opportunity_id,date,price,reason,roi
uuid-1,20230125,11.20,take_profit_stage1,0.067
uuid-2,20230120,10.31,stop_loss,-0.023
uuid-3,20230128,9.06,take_profit_stage2,0.105
```

---

## 工作原理

### 核心逻辑

```python
class OpportunityEnumeratorWorker:
    def _enumerate_single_day(self, tracker, current_kline, data_of_today):
        # 1. 检查所有 active opportunities
        for opportunity in tracker['active_opportunities']:
            is_completed = opportunity.check_targets(
                current_kline=current_kline,
                goal_config=self.settings.goal
            )
            
            if is_completed:
                # 移出 active list
                pass
        
        # 2. 扫描新机会（⭐ 不管是否有持仓）
        new_opportunity = self._scan_opportunity_with_data(data_of_today)
        
        if new_opportunity:
            tracker['active_opportunities'].append(new_opportunity)
            tracker['all_opportunities'].append(new_opportunity)
```

### Opportunity 实例方法

```python
class Opportunity:
    def check_targets(self, current_kline, goal_config) -> bool:
        """检查止盈止损"""
        # 检查各种止盈止损条件
        if completed:
            self._settle(...)  # 内部结算
            return True
        return False
    
    def settle(self, last_kline, reason='backtest_end'):
        """强制结算（回测结束时）"""
        self._settle(...)
```

---

## 使用场景

### 场景 1：开发调试（快速验证）

```python
# 缩小范围
OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20230110',     # ⭐ 只测试 10 天
    stock_list=['000001.SZ'], # ⭐ 只测试 1 只股票
    max_workers=1            # ⭐ 单进程，方便调试
)
```

### 场景 2：完整回测

```python
# 完整枚举
OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20231231',     # ⭐ 完整一年
    stock_list=all_stocks,   # ⭐ 所有股票
    max_workers=10           # ⭐ 全速并行
)
```

### 场景 3：CapitalAllocationSimulator 使用（未来）

```python
# Allocation 会自动调用 Enumerator
allocation_simulator.run(
    strategies=['momentum', 'value'],
    start_date='20230101',
    end_date='20231231',
    capital=100000
)
# 内部会调用 OpportunityEnumerator.enumerate(...)
```

---

## 性能

**测试场景**：100 股票，250 交易日

| 指标 | 预估值 | 说明 |
|------|--------|------|
| 枚举时间 | 30-60 秒 | 取决于策略复杂度 |
| CSV 文件大小 | 1-5 MB | 取决于机会数量 |
| 并行效率 | 线性加速 | `max_workers` 可调 |

**优化建议**：
- 调试时缩小范围（股票数量、时间范围）
- 生产环境增加 `max_workers`

---

## 常见问题

**Q: 每次都要重新计算吗？会不会很慢？**  
A: 是的，每次都重新计算。但这保证结果始终反映最新策略代码。如果需要缓存，将来在 `CapitalAllocationSimulator` 层实现。

**Q: 能不能读取之前的结果？**  
A: 可以，直接读取 CSV：
```python
import pandas as pd
df = pd.read_csv('results/opportunity_enumerator/momentum/20230101_20231231/opportunities.csv')
```

**Q: 枚举时间太长怎么办？**  
A: 
1. 增加 `max_workers`（如 20）
2. 缩小股票范围（先测试部分股票）
3. 缩小时间范围（先测试一个月）

**Q: 和 Simulator 有什么区别？**  
A: 
- **Simulator**：单一主线（模拟实际交易）
- **Enumerator**：完整枚举（所有可能的机会）
- Enumerator 的结果会被 `CapitalAllocationSimulator` 使用

---

## 设计原则

1. **完整性 > 性能**：不为性能牺牲准确性
2. **简单 > 复杂**：专注于生成，不管理缓存
3. **每次重新计算**：保证结果最新
4. **职责单一**：只负责枚举，不负责读取

---

**版本**：1.0（简化版）  
**完成时间**：2026-01-08
