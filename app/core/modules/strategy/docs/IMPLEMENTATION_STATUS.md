# Strategy 系统实现状态

**日期**: 2026-01-08  
**状态**: 🔄 设计完成，待实施

---

## 📋 核心设计决策

### 1. Settings 设计：字典结构（保持一致性）

**决策**：使用字典结构，与项目其他模块保持一致。

**结构**：
- per strategy 配置：`strategies/{name}/settings.py`（字典）
- 全局配置：`strategies/global_settings.py`（只有 Allocation）

**分层**：
```python
settings = {
    "data": {...},           # 数据配置
    "sampling": {...},       # 股票采样（per strategy）
    "simulator": {...},      # Simulator 专用
    "performance": {...}     # 性能配置（per strategy）
}
```

---

### 2. Indicators 配置：统一数组格式

**决策**：所有指标都用数组，参数统一。

**格式**：
```python
"indicators": {
    "ma": [{"period": 5}, {"period": 10}],
    "rsi": [{"period": 14}],
    "macd": [{"fast": 12, "slow": 26, "signal": 9}]
}
```

**适用范围**：只用于 K 线数据（不用于 GDP、财务数据等）

**工作流**：
1. 用户配置 → 2. 框架自动计算 → 3. 添加到 klines → 4. 用户直接使用

---

### 3. Pools/Blacklists：per strategy + 纯文本

**决策**：pools 和 blacklists 在策略文件夹下，纯文本格式。

**结构**：
```
strategies/example/
├── pools/
│   └── high_quality.txt    # 纯文本，一行一个股票代码
└── blacklists/
    └── st_stocks.txt
```

**配置**：
```python
"pool": {
    "id_list_path": "pools/high_quality.txt"  # 相对路径
}
```

---

### 4. OpportunityEnumerator 存储：CSV 双表

**决策**：CSV 双表（opportunities + targets）+ JSON 元信息

**原因**：数据量大，JSON 性能不够，CSV 文件小 5-8 倍，加载快 5 倍。

---



## 📋 实施计划

### Phase 1: Opportunity 模型增强 + OpportunityEnumerator（3 天）✅

**目标**：建立 Layer 0（底层公用组件）

**任务**：
1. **Opportunity 模型增强**（1 天）✅
   - [x] 添加 `check_targets()` 实例方法（止盈止损检查）
   - [x] 添加 `settle()` 实例方法（强制结算）
   - [x] 添加 `completed_targets` 字段（枚举器专用）
   - [x] Simulator 适配验证（使用实例方法）

2. **OpportunityEnumerator**（2 天）✅
   - [x] 实现完整枚举（每天都扫描）
   - [x] 实现 CSV 双表存储（opportunities.csv + targets.csv）
   - [x] 实现多进程并行
   - [x] 使用 Opportunity 实例方法
   - [x] 简化设计（去掉 mode、signal_window、use_cache）

**产出**：✅
- `app/core/modules/strategy/models/opportunity.py`（增强的模型）
  - `check_targets()` - 止盈止损检查
  - `settle()` - 强制结算
  - `completed_targets` - 完成目标列表
- `app/core/modules/strategy/components/opportunity_enumerator/`
  - `opportunity_enumerator.py`（Manager）
  - `enumerator_worker.py`（Worker）
  - `__init__.py`（模块入口）
  - `README.md`（使用文档）

**设计决策**：
- ❌ 删除 `mode`/`signal_window`：只保留完整枚举
- ❌ 删除 `use_cache`：专注于生成，不管理缓存
- ✅ 每次重新计算：保证结果最新
- ✅ 简单 > 复杂：职责单一

---

### Phase 2: CapitalAllocationSimulator 核心（2 天）

**目标**：实现资金分配模拟核心逻辑

**任务**：
1. **Step 1: 获取 Opportunities**（0.5 天）
   - [ ] 配置验证
   - [ ] 调用 OpportunityEnumerator.enumerate()
   - [ ] 添加策略信息（priority）

2. **Step 2: Timeline 构建**（0.5 天）
   - [ ] 事件驱动 Timeline
   - [ ] 买卖事件排序（先卖后买）

3. **Step 3: 执行模拟**（0.5 天）
   - [ ] Account 管理
   - [ ] 按时间轴推进
   - [ ] 优先级排序
   - [ ] 持仓管理

4. **Step 4: 结果输出**（0.5 天）
   - [ ] 统计计算
   - [ ] JSON 保存
   - [ ] 控制台输出

**产出**：
- `app/core/modules/capital_allocation_simulator/`
  - `capital_allocation_simulator.py`（主类）
  - `timeline_builder.py`（Timeline 构建）
  - `account.py`（账户管理）
  - `models.py`（数据模型）

---

### Phase 3: 测试和验证（2 天）

**任务**：
- [ ] OpportunityEnumerator 单元测试
- [ ] CapitalAllocationSimulator 单元测试
- [ ] 端到端集成测试
- [ ] 性能测试（CSV 加载速度）
- [ ] 对比验证

---

### Phase 4: 文档和示例（1 天）

**任务**：
- [ ] Settings 模板（单文件 + 类分层）
- [ ] 用户使用教程
- [ ] 配置说明
- [ ] 示例代码

---

## 📊 当前状态

### ✅ 已完成

**核心架构设计**：
- ✅ 四层架构（Layer 0-3）
- ✅ OpportunityEnumerator 设计
- ✅ CapitalAllocationSimulator 设计
- ✅ CSV 双表存储方案
- ✅ Settings 设计（类分层 + 继承）
- ✅ 设计文档（506 行，精简版）

**已实施模块**：
- ✅ StrategyManager（748 行）
- ✅ BaseStrategyWorker（445 行）
- ✅ StrategyWorkerDataManager（318 行）
- ✅ OpportunityService（295 行）
- ✅ SessionManager（84 行）
- ✅ IndicatorService（446 行）
- ✅ Opportunity 模型
- ✅ StrategySettings 模型

---

### 🔄 待实施（按 Phase 顺序）

| Phase | 模块 | 预计时间 | 优先级 | 状态 |
|-------|------|---------|--------|------|
| Phase 1 | OpportunityCalculator | 1 天 | P0 | ⏳ 待开始 |
| Phase 1 | OpportunityEnumerator | 2 天 | P0 | ⏳ 待开始 |
| Phase 2 | CapitalAllocationSimulator | 2 天 | P0 | ⏳ 待开始 |
| Phase 3 | 测试验证 | 2 天 | P0 | ⏳ 待开始 |
| Phase 4 | 文档示例 | 1 天 | P1 | ⏳ 待开始 |

**总计**：8 天（1.5 周）

---

## 🎯 核心技术栈

### Layer 0: OpportunityEnumerator

**存储方案**：CSV 双表
```
opportunities.csv  # 主表（~500 KB）
targets.csv       # 子表（~800 KB）
metadata.json     # 元信息（~5 KB）
```

**性能指标**：
- 文件大小：1-2 MB（vs JSON 5-10 MB）
- 加载速度：0.1-0.2 秒（vs JSON 0.5-1 秒）
- 用户友好：Excel 直接打开

**技术选型**：
- pandas：CSV 读写
- multiprocessing：并行枚举

---

### Layer 3: CapitalAllocationSimulator

**核心算法**：
- Timeline 构建：事件驱动（O(N) vs 时钟 Tick O(N×D)）
- 买卖顺序：先卖后买
- 优先级排序：用户定义

**数据模型**：
- Account（账户）
- Position（持仓）
- ExecutionRecord（执行记录）

---

## 📈 性能目标

| 指标 | 目标值 | 测试场景 |
|------|--------|---------|
| OpportunityEnumerator（简化版） | < 5 秒 | 100 股票，3 天窗口 |
| OpportunityEnumerator（完整版） | < 30 秒 | 100 股票，250 天，多进程 |
| CSV 加载 | < 0.2 秒 | 5000 opportunities |
| Timeline 构建 | < 1 秒 | 5000 opportunities |
| Allocation 模拟 | < 5 秒 | 2 策略，100 股票，1 年 |

---

## 🔧 开发环境要求

**Python 版本**：3.8+

**核心依赖**：
- pandas >= 2.0.0（CSV 读写）
- numpy >= 1.24.0
- pandas-ta-classic >= 0.3.59（技术指标）

**新增依赖**：无（复用现有）

---

## ✅ 验收标准

### Phase 1: OpportunityEnumerator

- [ ] 能够枚举单个策略的所有 opportunities
- [ ] CSV 文件正确生成（opportunities.csv + targets.csv）
- [ ] 缓存正确加载（pandas 读取）
- [ ] 多版本管理正常（latest 软链接）
- [ ] 性能达标（< 5 秒，简化版）

### Phase 2: CapitalAllocationSimulator

- [ ] 能够加载多个策略的 opportunities
- [ ] Timeline 正确构建（事件驱动）
- [ ] 资金约束正确执行（买入 vs 跳过）
- [ ] 优先级排序正确
- [ ] 统计结果正确（总收益、胜率等）

### Phase 3: 集成测试

- [ ] 端到端流程通过（Simulator → Enumerator → Allocation）
- [ ] 性能达标（全流程 < 1 分钟）
- [ ] 结果可复现

---

## 🚀 快速开始（Phase 1 完成后）

```python
# 1. 枚举 opportunities
from app.core.modules.opportunity_enumerator import OpportunityEnumerator

all_opps = OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20231231',
    stock_list=['000001.SZ', '000002.SZ'],
    mode='simplified',
    signal_window=3
)

# 2. 运行资金分配模拟
from app.core.modules.capital_allocation_simulator import CapitalAllocationSimulator

simulator = CapitalAllocationSimulator({
    'strategies': [
        {'name': 'momentum', 'priority': 1},
        {'name': 'value', 'priority': 2}
    ],
    'capital': {
        'initial_capital': 100000,
        'fixed_amount_per_trade': 5000
    }
})

result = simulator.run()
print(f"最终资金: {result['final_capital']}")
print(f"总收益: {result['total_return']}")
```

---

**下一步**：开始 Phase 1 实施！🎯
