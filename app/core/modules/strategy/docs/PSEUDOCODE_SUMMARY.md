# Strategy 系统伪代码总结

**日期**: 2025-12-19  
**状态**: 伪代码完成，待实现

---

## 已完成的伪代码文件

### 核心模块（app/core/modules/strategy/）

1. **strategy_manager.py** (651 行)
   - ✅ StrategyManager 类
   - ✅ 策略发现（discover_strategies）
   - ✅ Scanner 执行（execute_scan）
   - ✅ Simulator 执行（execute_simulate）
   - ✅ 作业构建（build_jobs）
   - ✅ 结果收集和保存

2. **base_strategy_worker.py** (307 行)
   - ✅ BaseStrategyWorker 基类
   - ✅ process_entity() 入口
   - ✅ scan_opportunity() 抽象方法
   - ✅ simulate_opportunity() 抽象方法
   - ✅ 钩子方法

3. **enums.py** (24 行)
   - ✅ ExecutionMode（scan/simulate）
   - ✅ OpportunityStatus（active/closed/expired）
   - ✅ SellReason（止盈/止损/到期）

---

### 核心模型（app/core/modules/strategy/models/）

4. **opportunity.py** (140 行)
   - ✅ Opportunity 类（完整字段定义）
   - ✅ Scanner 字段
   - ✅ Simulator 字段
   - ✅ 序列化方法（to_dict/from_dict）
   - ✅ 业务方法（is_valid, calculate_annual_return）

5. **strategy_settings.py** (83 行)
   - ✅ StrategySettings 类
   - ✅ CoreSettings
   - ✅ PerformanceSettings
   - ✅ DataRequirements
   - ✅ ExecutionSettings

---

### 核心组件（app/core/modules/strategy/components/）

6. **opportunity_service.py** (277 行)
   - ✅ OpportunityService 类
   - ✅ Scanner 结果保存（JSON）
   - ✅ Simulator 结果保存（JSON）
   - ✅ 加载机会（load_scan_opportunities）
   - ✅ Summary 计算

7. **session_manager.py** (84 行)
   - ✅ SessionManager 类
   - ✅ Session ID 生成
   - ✅ meta.json 管理

8. **strategy_worker_data_manager.py** (204 行)
   - ✅ StrategyWorkerDataManager 类
   - ✅ Scanner 数据加载（load_latest_data）
   - ✅ Simulator 数据加载（load_historical_data）
   - ✅ 数据访问接口（get_klines）

---

### 示例策略（app/userspace/strategies/example/）

9. **strategy_worker.py** (136 行)
   - ✅ ExampleStrategyWorker 实现
   - ✅ scan_opportunity() 示例
   - ✅ simulate_opportunity() 示例

10. **settings.py** (43 行)
    - ✅ 示例配置

---

## 文件结构总览

```
app/core/modules/strategy/
├── __init__.py                  # 模块导入
├── strategy_manager.py          # 策略管理器（651 行）
├── base_strategy_worker.py      # Worker 基类（307 行）
├── enums.py                     # 枚举（24 行）
│
├── models/                      # 核心模型
│   ├── __init__.py
│   ├── opportunity.py           # Opportunity 模型（140 行）
│   └── strategy_settings.py    # Settings 模型（83 行）
│
├── components/                  # 核心组件
│   ├── __init__.py
│   ├── opportunity_service.py  # JSON 存储服务（277 行）
│   ├── session_manager.py      # Session 管理（84 行）
│   └── strategy_worker_data_manager.py  # 数据管理（204 行）
│
└── docs/                        # 文档
    ├── DESIGN.md                # 设计文档（1444 行）
    └── PSEUDOCODE_SUMMARY.md    # 本文档

---

app/userspace/strategies/
├── README.md                    # 用户指南
└── example/                     # 示例策略
    ├── strategy_worker.py       # Worker 实现（136 行）
    ├── settings.py              # 配置（43 行）
    └── results/                 # 结果（自动生成）
        ├── scan/
        └── simulate/
```

**总计**: 11 个 Python 文件，约 **1823 行伪代码**

---

## 核心设计亮点

### 1. 类比 Tag 系统（95% 相似）

| Tag 系统 | Strategy 系统 |
|---------|--------------|
| TagManager | StrategyManager |
| BaseTagWorker | BaseStrategyWorker |
| TagWorkerDataManager | StrategyWorkerDataManager |
| tag_value 表 | JSON 文件 |

### 2. 职责单一

- **StrategyManager**: 发现、管理、调度
- **BaseStrategyWorker**: 处理单个股票
- **StrategyWorkerDataManager**: 数据加载
- **OpportunityService**: JSON 存储

### 3. 用户友好

用户只需实现两个方法：
```python
def scan_opportunity(self) -> Optional[Opportunity]:
    # 扫描逻辑
    pass

def simulate_opportunity(self, opportunity) -> Opportunity:
    # 回测逻辑
    pass
```

### 4. JSON 存储（直观）

- 按日期/session 组织
- 每个股票一个文件
- 包含 summary 汇总
- 添加 latest 软链接

---

## 执行流程（伪代码）

### Scanner 流程

```python
# 1. 主进程
manager = StrategyManager()
manager.execute_scan('momentum')

# 2. StrategyManager 执行
def execute_scan(strategy_name):
    # 2.1 加载全局缓存
    load_global_cache()  # 股票列表、交易日历
    
    # 2.2 构建 jobs
    jobs = [
        {'stock_id': '000001.SZ', 'execution_mode': 'scan', ...},
        {'stock_id': '000002.SZ', 'execution_mode': 'scan', ...},
        ...
    ]
    
    # 2.3 多进程执行
    results = ProcessWorker.execute(jobs)
    
    # 2.4 保存结果
    for result in results:
        if result['opportunity']:
            opportunity_service.save_scan_opportunities(...)

# 3. 子进程
class MomentumStrategyWorker(BaseStrategyWorker):
    def scan_opportunity():
        klines = self.data_manager.get_klines()
        
        if check_signal(klines):
            return Opportunity(...)
        
        return None
```

---

### Simulator 流程

```python
# 1. 主进程
manager = StrategyManager()
manager.execute_simulate('momentum')

# 2. StrategyManager 执行
def execute_simulate(strategy_name):
    # 2.1 加载历史机会
    opportunities = opportunity_service.load_scan_opportunities()
    
    # 2.2 创建 session
    session_id = session_manager.create_session()
    
    # 2.3 构建 jobs
    jobs = [
        {'stock_id': '000001.SZ', 'execution_mode': 'simulate', 'opportunity': {...}, ...},
        ...
    ]
    
    # 2.4 多进程执行
    results = ProcessWorker.execute(jobs)
    
    # 2.5 更新结果
    for result in results:
        opportunity_service.save_simulate_opportunities(...)

# 3. 子进程
class MomentumStrategyWorker(BaseStrategyWorker):
    def simulate_opportunity(opportunity):
        klines = self.data_manager.get_klines()
        
        # 遍历持有期
        for kline in klines:
            if check_stop_loss_or_take_profit(kline):
                break
        
        # 更新 opportunity
        opportunity.sell_date = ...
        opportunity.price_return = ...
        
        return opportunity
```

---

## 下一步

### 需要实现的功能

1. **StrategyManager**：
   - [ ] _discover_strategies() - 策略发现
   - [ ] _load_global_cache() - 全局缓存加载
   - [ ] _build_scan_jobs() - 构建扫描作业
   - [ ] _build_simulate_jobs() - 构建模拟作业

2. **BaseStrategyWorker**：
   - [ ] _execute_scan() - 扫描执行
   - [ ] _execute_simulate() - 模拟执行

3. **StrategyWorkerDataManager**：
   - [ ] _load_klines() - K-line 加载
   - [ ] _get_latest_trading_date() - 获取最新交易日
   - [ ] _get_date_before() - 日期计算

4. **OpportunityService**：
   - [ ] save_scan_opportunities() - 保存扫描结果
   - [ ] save_simulate_opportunities() - 保存模拟结果
   - [ ] _calculate_summary() - 计算汇总

5. **示例策略**：
   - [ ] 测试 scan 功能
   - [ ] 测试 simulate 功能

---

**伪代码完成，可以开始实现了！**
