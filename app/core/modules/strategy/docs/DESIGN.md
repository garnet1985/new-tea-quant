# Strategy 系统设计文档

**版本**: 1.0  
**日期**: 2025-12-19  
**最后更新**: 2025-12-19  
**状态**: 设计阶段

---

## 📋 目录

1. [概述](#概述)
2. [设计动机](#设计动机)
3. [核心概念](#核心概念)
4. [架构设计](#架构设计)
5. [内存管理](#内存管理)
6. [核心模块](#核心模块)
7. [核心模型](#核心模型)
8. [Indicator 组件](#indicator-组件)
9. [数据存储](#数据存储)
10. [执行流程](#执行流程)
11. [与 Legacy 系统的关系](#与-legacy-系统的关系)
12. [与 Tag 系统的对比](#与-tag-系统的对比)
13. [未来扩展](#未来扩展)

---

## 概述

### 系统定位

Strategy 系统是一个**策略管理和回测框架**，用于：
- **发现投资机会**（Scanner）：扫描股票，发现买入信号
- **回测策略效果**（Simulator）：使用历史数据验证策略表现
- **管理策略生命周期**（StrategyManager）：发现、验证、执行用户策略

### 核心特点

- ✅ **类比 Tag 系统**：Manager → Worker → DataManager 架构
- ✅ **多进程并行**：使用 ProcessWorker 高效处理海量股票
- ✅ **面向对象**：Opportunity 核心模型
- ✅ **用户友好**：用户只需实现核心逻辑，框架处理其他
- ✅ **关注价格变化**：只分析股价波动，不涉及金额管理
- ✅ **JSON 存储**：直观易读，无需 SQL 知识

### 设计原则

1. **职责单一**：每个模块只负责一件事
2. **简单优先**：当前阶段只关注策略效果，不涉及资金管理
3. **可扩展**：为未来的 Portfolio 系统预留接口
4. **类比成功**：复制 Tag 系统的成功经验
5. **兼容 Legacy**：复用 Legacy 代码，平滑迁移

---

## 设计动机

### 动机 1: 面向对象抽象

**当前问题**：
- Legacy 系统数据主要通过字典传递（`Dict[str, Any]`）
- 缺少类型安全和清晰的数据模型
- 难以跨模块共享（如 Opportunity 在 Adapter 中使用）

**解决方案**：
引入核心对象抽象：
- **Opportunity**：投资机会（唯一核心对象）
- **StrategySettings**：策略配置（类型安全）

**价值**：
- ✅ 类型安全：IDE 自动补全，减少拼写错误
- ✅ 易于维护：对象模型比字典更清晰
- ✅ 跨模块复用：统一的数据模型
- ✅ 易于扩展：对象可以添加方法

---

### 动机 2: BaseStrategyWorker 设计

**当前问题**：
- Legacy BaseStrategy 职责过多（扫描、模拟、表管理、数据加载...）
- 难以测试（需要完整实例）
- 多进程困难（对象太复杂）
- 难以扩展（所有功能耦合）

**解决方案**：
类比 Tag 系统的 BaseTagWorker：
```python
class BaseStrategyWorker:
    def __init__(self, job_payload)           # 只在子进程实例化
    def process_entity() -> Result            # 处理单个股票
    def scan_opportunity() -> Opportunity     # 用户实现（扫描）
    def simulate_opportunity() -> Opportunity # 用户实现（回测）
```

**价值**：
- ✅ 职责单一：Worker 只负责核心逻辑
- ✅ 类比成功设计：Tag 系统已验证可行
- ✅ 多进程友好：轻量级对象，易于序列化
- ✅ 易于测试：可以单独测试 Worker 逻辑

---

## 核心概念

### 等量交易

**定义**：
- ✅ 只关注**股价波动**（价格变化）
- ✅ 不分析**金钱盈亏**（不涉及金额）
- ✅ 只分析**价格收益率 ROI**（如 +5%、-3%）
- ✅ 基本等于只关注**一股的数据**

**示例**：
```
买入价格：10 元
卖出价格：11 元
收益率：(11 - 10) / 10 = 10%

不关心买了多少股，不关心赚了多少钱，只关心价格涨了 10%
```

**为什么这样设计？**
- ✅ 关注策略本身的效果（价格预测能力）
- ✅ 简化实现（不涉及资金管理、手续费等）
- ✅ 独立性（策略效果与资金规模无关）
- ✅ 为 Portfolio 系统预留接口（资金管理是 Portfolio 的职责）

---

### Scanner vs Simulator

#### Scanner（扫描器）

**作用**：发现当前的投资机会

**数据范围**：
- 只扫描**最新一天**的数据
- 提供必要的历史窗口（如最近 60 天用于计算指标）

**输出**：
- Opportunity 对象（包含触发信息）
- status = "active"
- 保存到 JSON 文件

**用途**：
- 实盘提示（今天有哪些买入机会）
- 机会跟踪

---

#### Simulator（模拟器）

**作用**：回测历史机会的效果

**数据范围**：
- 从触发日期到结束日期的**历史数据**

**输出**：
- 更新 Opportunity 对象（添加回测结果）
- status = "closed"
- 保存到 JSON 文件

**用途**：
- 策略验证
- 参数优化
- 历史表现分析

---

### Scanner 和 Simulator 的关系

**完全独立**：
- ❌ 不支持 both 模式（同时扫描和模拟）
- ❌ 不需要关注数据传递（它们不会交叉）

**执行流程**：
```
Scanner 流程：
扫描股票 → 发现机会 → 保存 Opportunity (JSON) → 结束

Simulator 流程：
加载历史 Opportunity (JSON) → 回测 → 更新 Opportunity (JSON) → 结束
```

**它们是两条不同的线路！**

---

## 架构设计

### 整体架构

```
app/core/modules/strategy/
├── strategy_manager.py          # 策略管理器（类比 TagManager）
├── base_strategy_worker.py      # 策略 Worker 基类（类比 BaseTagWorker）
├── enums.py                     # 枚举定义
│
├── models/                      # 核心模型
│   ├── opportunity.py           # 投资机会模型
│   └── strategy_settings.py    # 策略配置模型
│
├── components/                  # 核心组件
│   ├── strategy_worker_data_manager.py  # 数据管理器（类比 TagWorkerDataManager）
│   ├── opportunity_service.py   # 机会服务（JSON 存储）
│   └── session_manager.py       # Session 管理（生成 session_id）
│
└── docs/                        # 文档
    └── DESIGN.md                # 本文档

---

app/userspace/strategies/        # 用户策略（类比 userspace/tags）
├── momentum/
│   ├── strategy_worker.py       # 策略实现
│   ├── settings.py              # 策略配置
│   └── results/                 # 结果存储（JSON）
│       ├── scan/                # 扫描结果
│       │   ├── 2025_12_19/      # 按日期组织
│       │   │   ├── summary.json
│       │   │   └── 000001.SZ.json
│       │   └── latest -> 2025_12_19/
│       └── simulate/            # 模拟结果
│           ├── session_001/     # 按 session 组织
│           │   ├── summary.json
│           │   └── 000001.SZ.json
│           └── latest -> session_001/
│
├── mean_reversion/
└── ...
```

---

### 模块职责

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **StrategyManager** | 发现、管理用户策略；构建作业；多进程执行 | userspace/strategies | Opportunity 列表 |
| **BaseStrategyWorker** | 处理单个股票的扫描或回测 | job_payload | Opportunity |
| **StrategyWorkerDataManager** | 数据加载、缓存、过滤 | stock_id, date_range | K-line, 财务数据等 |
| **OpportunityService** | Opportunity 的 JSON 存储管理 | Opportunity | JSON 文件 |
| **SessionManager** | Session ID 管理 | strategy_name | session_id |

---

### 与 Tag 系统的类比

| Tag 系统 | Strategy 系统 | 说明 |
|---------|--------------|------|
| TagManager | StrategyManager | 发现和管理 |
| BaseTagWorker | BaseStrategyWorker | Worker 基类 |
| TagWorkerDataManager | StrategyWorkerDataManager | 数据管理 |
| process_entity() | process_entity() | 处理单个实体 |
| calculate_tag() | scan_opportunity() / simulate_opportunity() | 核心逻辑 |
| tag_value | Opportunity | 输出对象 |
| app/userspace/tags | app/userspace/strategies | 用户空间 |

**相似度：95%**

**核心差异**：
- Tag：单一核心逻辑（calculate_tag）
- Strategy：双核心逻辑（scan_opportunity + simulate_opportunity）
- Tag：数据库存储
- Strategy：JSON 文件存储

---

## 内存管理

### 核心原则

#### ✅ 可以缓存的数据（全局级别）

**位置**: `StrategyManager.global_cache`

**特点**:
- 数据量小
- 全局共享
- 生命周期：一次扫描/模拟

**示例**:
- ✅ `stock_list` - 股票列表（几千条记录）
- ✅ `GDP` - 宏观经济数据
- ✅ `LPR` - 利率数据
- ✅ `trading_dates` - 交易日历

#### ❌ 不可以缓存的数据（股票级别）

**位置**: `StrategyWorkerDataManager._current_data`

**特点**:
- 数据量大（每只股票几千到上万条记录）
- 单个股票独有
- 生命周期：仅在 Worker 实例存活期间

**示例**:
- ❌ `股票 K线` - 每只股票数千条记录
- ❌ `公司财务数据` - 每只股票数百条记录
- ❌ `Tag 数据` - 每只股票数千条记录

### 内存管理架构

```
StrategyManager（主进程）
├─ global_cache（全局缓存，数据量小）
│  ├─ stock_list ✅
│  ├─ trading_dates ✅
│  └─ macro_data ✅
│
└─ ProcessWorker（多进程执行）
    ├─ Worker 1（子进程）
    │  └─ StrategyWorkerDataManager
    │     └─ _current_data（临时数据，Worker 销毁时清理）
    │        ├─ klines ❌
    │        └─ finance ❌
    │
    ├─ Worker 2（子进程）
    │  └─ StrategyWorkerDataManager
    │     └─ _current_data（临时数据）
    │
    └─ Worker N（子进程）
```

### 内存占用估算

**单只股票数据量**:
- K线数据：1000 条 × 100 字节 = **100KB**
- 财务数据：100 条 × 200 字节 = **20KB**
- Tag 数据：1000 条 × 50 字节 = **50KB**
- **单只股票总计**: ~170KB

**多进程并发**:
- 8 个 Worker: 8 × 170KB = **~1.4MB** ✅
- 5000 只股票（无控制）: 5000 × 170KB = **~850MB** ⚠️ 危险！

### 正确设计

**Worker 级别的数据管理**:

```python
class StrategyWorkerDataManager:
    """
    数据管理器（Worker 级别）
    
    重要：
    - 只管理当前股票的数据
    - 不是全局缓存
    - Worker 销毁时自动清理
    """
    
    def __init__(self, stock_id, settings, data_mgr):
        # 临时数据存储（不是缓存！）
        # 生命周期：仅在当前 Worker 实例存活期间
        self._current_data = {
            'klines': [],
            'finance': []
        }
```

**控制 Worker 数量**:

```python
class StrategyManager:
    def _get_max_workers(self, config_value):
        """控制 Worker 数量 = 控制内存使用"""
        if config_value == 'auto':
            cpu_count = os.cpu_count() or 4
            return max(1, cpu_count - 1)  # 通常 4-8 个
        return int(config_value)
```

### 最佳实践

1. **明确区分缓存和临时数据**
   - 全局缓存（数据量小）：`StrategyManager.global_cache`
   - 临时数据（Worker 级别）：`StrategyWorkerDataManager._current_data`

2. **通过命名体现设计意图**
   - ❌ `self.data_cache` - 容易误解为全局缓存
   - ✅ `self._current_data` - 明确是临时数据

3. **限制 Worker 数量**
   - 推荐：`max_workers: 'auto'` （4-8 个）
   - 谨慎：手动设置大数值

### 内存管理总结

| 数据类型 | 位置 | 缓存 | 生命周期 | 内存影响 |
|---------|------|------|---------|---------|
| 股票列表 | StrategyManager | ✅ | 一次扫描/模拟 | 小（~KB） |
| 宏观数据 | StrategyManager | ✅ | 一次扫描/模拟 | 小（~KB） |
| 股票K线 | Worker | ❌ | Worker 实例 | 大（~100KB/股票） |
| 财务数据 | Worker | ❌ | Worker 实例 | 中（~20KB/股票） |

**核心原则**: 全局数据（小）→ 可缓存；股票数据（大）→ 不缓存，通过限制 Worker 数量控制内存。

---

## 核心模块

### 1. StrategyManager

**职责**：策略管理器（主进程）

**核心功能**：
1. **发现策略**：从 `app/userspace/strategies` 发现用户策略
2. **验证配置**：验证 settings.py 的有效性
3. **构建作业**：为每个股票构建 job_payload
4. **多进程执行**：使用 ProcessWorker 并行处理
5. **收集结果**：汇总 Worker 返回的结果
6. **缓存管理**：管理全局缓存（股票列表、交易日历、宏观数据）

**关键方法**：
```python
class StrategyManager:
    def __init__(self):
        self.strategy_cache = {}
        self.global_cache = {}  # 全局缓存
    
    def discover_strategies(self):
        """发现用户策略（类比 TagManager）"""
        pass
    
    def execute_scan(self, strategy_name: str):
        """执行扫描（Scanner 模式）"""
        # 1. 加载全局缓存
        # 2. 获取股票列表
        # 3. 构建 scan jobs
        # 4. 多进程执行
        # 5. 保存 Opportunity (JSON)
        pass
    
    def execute_simulate(self, strategy_name: str, session_id: str = None):
        """执行回测（Simulator 模式）"""
        # 1. 加载全局缓存
        # 2. 加载历史 Opportunities (JSON)
        # 3. 构建 simulate jobs
        # 4. 多进程执行
        # 5. 更新 Opportunity (JSON)
        pass
    
    def _load_global_cache(self):
        """加载全局缓存（生命周期：一次扫描/模拟）"""
        self.global_cache['stock_list'] = ...
        self.global_cache['trading_dates'] = ...
        self.global_cache['macro_data'] = ...
```

---

### 2. BaseStrategyWorker

**职责**：策略 Worker 基类（子进程）

**核心功能**：
1. **初始化**：接收 job_payload，初始化数据管理器
2. **处理实体**：统一入口 process_entity()
3. **扫描机会**：scan_opportunity()（用户实现）
4. **回测机会**：simulate_opportunity()（用户实现）

**关键方法**：
```python
class BaseStrategyWorker(ABC):
    def __init__(self, job_payload: Dict[str, Any]):
        """初始化（只在子进程调用）"""
        self.stock_id = job_payload['stock_id']
        self.strategy_name = job_payload['strategy_name']
        self.execution_mode = job_payload['execution_mode']  # 'scan' or 'simulate'
        
        # 解析配置
        self.settings = StrategySettings.from_dict(job_payload['settings'])
        
        # 初始化数据管理器
        self.data_manager = StrategyWorkerDataManager(
            stock_id=self.stock_id,
            settings=self.settings,
            data_mgr=DataManager()
        )
        
        # Simulate 模式特有
        if self.execution_mode == 'simulate':
            self.opportunity = Opportunity.from_dict(job_payload['opportunity'])
    
    def process_entity(self) -> Dict[str, Any]:
        """处理单个股票（子进程入口）"""
        if self.execution_mode == 'scan':
            return self._execute_scan()
        elif self.execution_mode == 'simulate':
            return self._execute_simulate()
    
    def _execute_scan(self) -> Dict[str, Any]:
        """执行扫描"""
        # 1. 加载数据
        self.data_manager.load_latest_data(lookback=60)
        
        # 2. 调用用户实现
        opportunity = self.scan_opportunity()
        
        # 3. 返回结果
        return {
            "success": True,
            "stock_id": self.stock_id,
            "opportunity": opportunity.to_dict() if opportunity else None
        }
    
    def _execute_simulate(self) -> Dict[str, Any]:
        """执行回测"""
        # 1. 加载历史数据
        self.data_manager.load_historical_data(
            start_date=self.opportunity.trigger_date,
            end_date=self.end_date
        )
        
        # 2. 调用用户实现
        updated_opportunity = self.simulate_opportunity(self.opportunity)
        
        # 3. 返回结果
        return {
            "success": True,
            "stock_id": self.stock_id,
            "opportunity": updated_opportunity.to_dict()
        }
    
    # ===== 抽象方法（用户实现）=====
    
    @abstractmethod
    def scan_opportunity(self) -> Optional[Opportunity]:
        """
        扫描投资机会（用户实现）
        
        Returns:
            Optional[Opportunity]: 如果发现机会，返回 Opportunity 对象
        """
        pass
    
    @abstractmethod
    def simulate_opportunity(self, opportunity: Opportunity) -> Opportunity:
        """
        回测机会（用户实现）
        
        Args:
            opportunity: 要回测的机会
        
        Returns:
            Opportunity: 更新后的机会（包含回测结果）
        """
        pass
```

---

### 3. StrategyWorkerDataManager

**职责**：数据管理器（类比 TagWorkerDataManager）

**核心功能**：
1. **数据加载**：加载 K-line、财务等数据
2. **缓存管理**：缓存数据，避免重复加载
3. **日期过滤**：按日期过滤数据

**关键方法**：
```python
class StrategyWorkerDataManager:
    def __init__(self, stock_id: str, settings: StrategySettings, data_mgr: DataManager):
        self.stock_id = stock_id
        self.settings = settings
        self.data_mgr = data_mgr
        self.data_cache = {}
    
    def load_latest_data(self, lookback: int = 60):
        """加载最新数据（Scanner 使用）"""
        latest_date = self._get_latest_trading_date()
        start_date = self._get_date_before(latest_date, lookback)
        
        klines = self._load_klines(start_date, latest_date)
        self.data_cache['klines'] = klines
        
        # 加载其他数据
        for entity in self.settings.data_requirements.required_entities:
            data = self._load_entity(entity, start_date, latest_date)
            self.data_cache[entity] = data
    
    def load_historical_data(self, start_date: str, end_date: str):
        """加载历史数据（Simulator 使用）"""
        klines = self._load_klines(start_date, end_date)
        self.data_cache['klines'] = klines
        
        # 加载其他数据
        for entity in self.settings.data_requirements.required_entities:
            data = self._load_entity(entity, start_date, end_date)
            self.data_cache[entity] = data
    
    def get_klines(self) -> List[Dict]:
        """获取 K-line 数据"""
        return self.data_cache.get('klines', [])
    
    def get_entity_data(self, entity_type: str) -> List[Dict]:
        """获取其他实体数据"""
        return self.data_cache.get(entity_type, [])
```

---

### 4. OpportunityService

**职责**：Opportunity 的 JSON 存储管理

**核心功能**：
1. **保存扫描结果**：保存到 `scan/{date}/` 文件夹
2. **保存模拟结果**：保存到 `simulate/{session_id}/` 文件夹
3. **加载机会**：从 JSON 文件加载
4. **生成 Summary**：汇总统计信息

**关键方法**：
```python
class OpportunityService:
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.base_path = Path(f"app/userspace/strategies/{strategy_name}/results")
        self.scan_path = self.base_path / "scan"
        self.simulate_path = self.base_path / "simulate"
    
    def save_scan_opportunity(self, opportunity: Opportunity):
        """保存扫描结果"""
        date = opportunity.scan_date
        dir_path = self.scan_path / date
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / f"{opportunity.stock_id}.json"
        
        # 读取现有数据（如果存在）
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
        else:
            data = {
                "stock": {"id": opportunity.stock_id, "name": opportunity.stock_name},
                "opportunities": [],
                "summary": {}
            }
        
        # 添加新机会
        data['opportunities'].append(opportunity.to_dict())
        
        # 更新 summary
        data['summary'] = self._calculate_summary(data['opportunities'])
        
        # 保存
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 更新 latest 软链接
        self._update_latest_link(self.scan_path, date)
    
    def load_scan_opportunities(self, date: str = None) -> List[Opportunity]:
        """加载扫描结果"""
        if date is None:
            # 加载最新
            latest_link = self.scan_path / "latest"
            if not latest_link.exists():
                return []
            date = latest_link.resolve().name
        
        dir_path = self.scan_path / date
        if not dir_path.exists():
            return []
        
        opportunities = []
        for file_path in dir_path.glob("*.json"):
            if file_path.name == "summary.json":
                continue
            with open(file_path, 'r') as f:
                data = json.load(f)
            for opp_dict in data['opportunities']:
                opportunities.append(Opportunity.from_dict(opp_dict))
        
        return opportunities
```

---

## 核心模型

### Opportunity（投资机会）

**定义**：表示策略发现的投资机会（唯一核心对象）

**职责**：
- Scanner 阶段：记录触发信息（trigger_date, trigger_price）
- Simulator 阶段：记录回测结果（sell_date, price_return）

**完整定义**：
```python
@dataclass
class Opportunity:
    """投资机会"""
    
    # ===== 基本信息 =====
    opportunity_id: str              # 机会唯一ID（UUID）
    stock_id: str                    # 股票代码
    stock_name: str                  # 股票名称
    strategy_name: str               # 策略名称
    strategy_version: str            # 策略版本
    
    # ===== Scanner 阶段字段 =====
    scan_date: str                   # 扫描日期
    trigger_date: str                # 触发日期（买入信号日期）
    trigger_price: float             # 触发价格（买入价格）
    trigger_conditions: Dict[str, Any]  # 触发条件（JSON）
    expected_return: Optional[float] # 预期收益率
    confidence: Optional[float]      # 置信度（0-1）
    
    # ===== Simulator 阶段字段 =====
    sell_date: Optional[str]         # 卖出日期
    sell_price: Optional[float]      # 卖出价格
    sell_reason: Optional[str]       # 卖出原因（止盈/止损/到期）
    
    # ===== 收益分析（基于价格）=====
    price_return: Optional[float]    # 价格收益率 = (sell_price - trigger_price) / trigger_price
    holding_days: Optional[int]      # 持有天数
    max_price: Optional[float]       # 持有期间最高价
    min_price: Optional[float]       # 持有期间最低价
    max_drawdown: Optional[float]    # 最大回撤（基于价格）
    
    # ===== 持有期追踪 =====
    tracking: Optional[Dict[str, Any]]  # 持有期间的详细追踪数据（JSON）
        # {
        #   "daily_prices": [10.50, 10.60, ...],
        #   "daily_returns": [0, 0.01, ...],
        #   "max_reached_date": "20251225",
        #   "min_reached_date": "20251222"
        # }
    
    # ===== 状态管理 =====
    status: str                      # 状态（active/testing/closed/expired）
    expired_date: Optional[str]      # 失效日期
    expired_reason: Optional[str]    # 失效原因
    
    # ===== 版本控制 =====
    config_hash: str                 # 策略配置的 hash
    
    # ===== 元数据 =====
    created_at: str                  # 创建时间
    updated_at: str                  # 更新时间
    metadata: Dict[str, Any]         # 其他元数据（JSON）
    
    # ===== 方法 =====
    def is_valid(self) -> bool:
        """验证机会是否有效"""
        return self.status == 'active'
    
    def is_closed(self) -> bool:
        """是否已回测完成"""
        return self.status == 'closed'
    
    def calculate_annual_return(self) -> float:
        """计算年化收益率"""
        if not self.price_return or not self.holding_days:
            return 0.0
        return self.price_return * (250 / self.holding_days)  # 250 个交易日
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典（用于序列化）"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Opportunity':
        """从字典创建（用于反序列化）"""
        return cls(**data)
```

---

### StrategySettings（策略配置）

**定义**：表示策略配置（类型安全）

**完整定义**：
```python
@dataclass
class StrategySettings:
    """策略配置"""
    
    # ===== 基本信息 =====
    name: str                        # 策略名称
    version: str                     # 策略版本
    description: str                 # 策略描述
    
    # ===== 核心配置 =====
    core: CoreSettings               # 核心配置
    performance: PerformanceSettings # 性能配置
    
    # ===== 数据需求 =====
    data_requirements: DataRequirements  # 数据需求
    
    # ===== 执行配置 =====
    execution: ExecutionSettings     # 执行配置
    
    # ===== 策略参数 =====
    params: Dict[str, Any]           # 策略特定参数
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategySettings':
        """从字典创建"""
        return cls(
            name=data['name'],
            version=data['version'],
            description=data.get('description', ''),
            core=CoreSettings(**data['core']),
            performance=PerformanceSettings(**data['performance']),
            data_requirements=DataRequirements(**data['data_requirements']),
            execution=ExecutionSettings(**data['execution']),
            params=data.get('params', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return asdict(self)


@dataclass
class CoreSettings:
    """核心配置"""
    entity_type: str                 # 实体类型（stock/index）
    start_date: str                  # 开始日期
    end_date: str                    # 结束日期


@dataclass
class PerformanceSettings:
    """性能配置"""
    max_workers: int                 # 最大进程数


@dataclass
class DataRequirements:
    """数据需求"""
    base_entity: str                 # 基础数据（如 stock_kline_daily）
    required_entities: List[str]     # 依赖数据（如 corporate_finance）


@dataclass
class ExecutionSettings:
    """执行配置"""
    stop_loss: float                 # 止损比例（如 -0.05 = -5%）
    take_profit: float               # 止盈比例（如 0.10 = 10%）
    max_holding_days: int            # 最大持有天数（如 20）
```

---

## Indicator 组件

### 概述

`IndicatorService` 是技术指标计算服务，作为 `pandas-ta-classic` 库的代理层，提供：
- ✅ **150+ 技术指标**：支持所有 pandas-ta-classic 的指标
- ✅ **便捷 API**：常用指标的快速调用方法
- ✅ **通用 API**：支持任意指标的通用接口
- ✅ **自动数据转换**：`List[Dict]` ↔ `DataFrame` 无缝转换
- ✅ **静态工具类**：无需实例化，直接调用
- ✅ **按需计算**：不缓存（除非发现性能瓶颈）

### 设计原则

**Proxy 模式**：不搬运 150+ 个指标的代码，直接代理到底层库
- 用户调用 → `IndicatorService` → 数据转换 → `pandas-ta-classic` → 返回结果
- 职责单一：只做数据转换和方法转发

**不缓存计算结果**：
- 指标计算速度快（毫秒级）
- 避免内存占用
- 等发现性能瓶颈再优化

### 核心 API

#### 1. 便捷 API（常用指标）

```python
from app.core.modules.indicator import IndicatorService

# 移动平均（MA）
ma20 = IndicatorService.ma(klines, length=20)
# 返回: [10.1, 10.2, 10.3, ...]

# 相对强弱指标（RSI）
rsi14 = IndicatorService.rsi(klines, length=14)
# 返回: [45.2, 48.3, 52.1, ...]

# MACD
macd = IndicatorService.macd(klines, fast=12, slow=26, signal=9)
# 返回: {
#     'MACD_12_26_9': [...],
#     'MACDs_12_26_9': [...],
#     'MACDh_12_26_9': [...]
# }

# 布林带（Bollinger Bands）
bbands = IndicatorService.bbands(klines, length=20, std=2.0)
# 返回: {
#     'BBL_20_2.0': [...],  # 下轨
#     'BBM_20_2.0': [...],  # 中轨
#     'BBU_20_2.0': [...]   # 上轨
# }

# 真实波动幅度（ATR）
atr = IndicatorService.atr(klines, length=14)

# 随机指标（KDJ）
stoch = IndicatorService.stoch(klines, k=14, d=3, smooth_k=3)

# 平均趋向指数（ADX）
adx = IndicatorService.adx(klines, length=14)

# 能量潮（OBV）
obv = IndicatorService.obv(klines)
```

#### 2. 通用 API（支持所有指标）

```python
# 支持 pandas-ta-classic 的所有 150+ 指标
result = IndicatorService.calculate(indicator_name, klines, **params)

# 示例：CCI（顺势指标）
cci = IndicatorService.calculate('cci', klines, length=20)

# 示例：Williams %R
willr = IndicatorService.calculate('willr', klines, length=14)

# 示例：Stochastic Oscillator
stoch = IndicatorService.calculate('stoch', klines, k=14, d=3)
```

### 在策略中使用

```python
class MyStrategyWorker(BaseStrategyWorker):
    def scan_opportunity(self):
        # 获取 K 线数据
        klines = self.data_manager.get_klines()
        
        if len(klines) < 60:
            return None
        
        # 方式1: 使用便捷 API（推荐）
        ma20 = IndicatorService.ma(klines, length=20)
        ma60 = IndicatorService.ma(klines, length=60)
        rsi = IndicatorService.rsi(klines, length=14)
        
        # 策略逻辑：金叉 + RSI 超卖
        if ma20[-1] > ma60[-1] and rsi[-1] < 30:
            return Opportunity(
                opportunity_id=str(uuid.uuid4()),
                stock_id=self.stock_id,
                trigger_date=klines[-1]['date'],
                trigger_price=klines[-1]['close'],
                trigger_conditions={
                    'ma20': ma20[-1],
                    'ma60': ma60[-1],
                    'rsi': rsi[-1],
                    'signal': 'golden_cross_oversold'
                }
            )
        
        # 方式2: 使用通用 API
        cci = IndicatorService.calculate('cci', klines, length=20)
        if cci[-1] > 100:  # CCI 超买
            return Opportunity(...)
        
        return None
```

### 数据格式

**输入格式**（我们的 K 线格式）:
```python
klines = [
    {
        'date': '20251219',
        'open': 10.0,
        'high': 10.5,
        'low': 9.8,
        'close': 10.2,
        'volume': 1000
    },
    ...
]
```

**输出格式**:
- **单列指标**（MA, RSI, ATR 等）: `List[float]`
  ```python
  [10.1, 10.2, 10.3, ...]
  ```

- **多列指标**（MACD, BBANDS 等）: `Dict[str, List[float]]`
  ```python
  {
      'MACD_12_26_9': [...],
      'MACDs_12_26_9': [...],
      'MACDh_12_26_9': [...]
  }
  ```

### 工具方法

```python
# 列出所有可用指标
all_indicators = IndicatorService.list_indicators()
# ['adx', 'atr', 'bbands', 'cci', 'macd', 'rsi', 'sma', ...]

# 查看指标帮助文档
help_text = IndicatorService.get_indicator_help('macd')
```

### 技术栈

- **底层库**: `pandas-ta-classic` 0.3.59
  - 社区维护，免费开源
  - 纯 Python 实现，易安装
  - 150+ 技术指标
  - 活跃维护，定期更新

- **依赖**:
  - `pandas >= 2.0.0`
  - `numpy >= 2.0.0`

### 性能考虑

**计算速度**:
- 单个指标计算：< 10ms（1000 条 K 线）
- 性能目标：< 200ms（用户可接受）
- 实测：绝大多数指标远低于目标

**内存占用**:
- 不缓存计算结果
- 按需计算，用完即释放
- 内存占用：可忽略

**未来优化**（如果需要）:
1. Worker 级别缓存（生命周期：单个股票处理期间）
2. 批量计算优化（共享中间结果）
3. 切换到 TA-Lib（C 实现，快 4 倍）

### 扩展性

**自定义指标**（未来）:
```python
# 用户可以注册自定义指标
def my_custom_indicator(klines, period):
    # 自定义计算逻辑
    return result

# 注册（TODO：未来功能）
IndicatorService.register('my_indicator', my_custom_indicator)
```

**切换底层库**（未来）:
```python
# 在 IndicatorService 中添加 backend 参数
# 支持切换到 TA-Lib 等其他库
```

### 最佳实践

1. **检查数据长度**
   ```python
   klines = self.data_manager.get_klines()
   if len(klines) < 60:  # 确保有足够数据
       return None
   ```

2. **处理 None 返回**
   ```python
   ma20 = IndicatorService.ma(klines, 20)
   if ma20 is None:  # 数据不足或计算失败
       return None
   ```

3. **使用便捷 API**
   ```python
   # ✅ 推荐：便捷 API
   ma20 = IndicatorService.ma(klines, 20)
   
   # ⚠️ 也可以：通用 API
   ma20 = IndicatorService.calculate('sma', klines, length=20)
   ```

4. **参数化配置**
   ```python
   # settings.py
   "params": {
       "ma_short": 20,
       "ma_long": 60,
       "rsi_period": 14
   }
   
   # strategy_worker.py
   params = self.settings.params
   ma_short = IndicatorService.ma(klines, params['ma_short'])
   ```

---

## 数据存储

### JSON 文件存储（采用方案）

#### 设计理由

**选择 JSON 的原因**：
1. ✅ **直观易读**（最重要）：可以直接打开文件查看，无需 SQL
2. ✅ **符合用户习惯**：Legacy 系统已经使用 JSON
3. ✅ **无需数据库**：降低使用门槛
4. ✅ **易于分享和备份**：文件可以直接复制、压缩
5. ✅ **开发友好**：调试时可以直接查看
6. ✅ **数据量小**：每次回测数据量不大（< 10MB），JSON 性能足够

---

### 文件结构

```
app/userspace/strategies/{strategy_name}/
├── strategy_worker.py
├── settings.py
└── results/                     # 结果存储（改名：tmp → results）
    ├── meta.json                # 策略元信息
    ├── scan/                    # 扫描结果
    │   ├── 2025_12_19/          # 按日期组织
    │   │   ├── summary.json     # 汇总信息
    │   │   ├── 000001.SZ.json   # 单股票机会
    │   │   └── ...
    │   └── latest -> 2025_12_19/  # 软链接到最新
    │
    └── simulate/                # 模拟结果
        ├── session_001/         # Session 文件夹
        │   ├── summary.json     # Session 汇总
        │   ├── 000001.SZ.json   # 单股票回测结果
        │   └── ...
        └── latest -> session_001/  # 软链接到最新
```

**关键改进（相比 Legacy）**：
1. ✅ `tmp` → `results`（更语义化）
2. ✅ 分离 `scan/` 和 `simulate/`（职责清晰）
3. ✅ 添加 `latest` 软链接（快速访问最新结果）
4. ✅ 扫描按日期组织（更直观）

---

### JSON 文件格式

#### 1. Scanner 输出：`scan/{date}/{stock_id}.json`

```json
{
  "stock": {
    "id": "000001.SZ",
    "name": "平安银行"
  },
  "opportunities": [
    {
      "opportunity_id": "uuid-1",
      "stock_id": "000001.SZ",
      "stock_name": "平安银行",
      "strategy_name": "momentum",
      "strategy_version": "1.0",
      
      "scan_date": "20251219",
      "trigger_date": "20251219",
      "trigger_price": 10.50,
      "trigger_conditions": {
        "momentum": 0.08,
        "volume_ratio": 1.5
      },
      "expected_return": 0.10,
      "confidence": 0.75,
      
      "status": "active",
      "config_hash": "abc123",
      "created_at": "2025-12-19T10:30:00",
      "updated_at": "2025-12-19T10:30:00",
      "metadata": {}
    }
  ],
  "summary": {
    "total_opportunities": 1,
    "avg_expected_return": 0.10,
    "avg_confidence": 0.75
  }
}
```

---

#### 2. Simulator 输出：`simulate/{session_id}/{stock_id}.json`

```json
{
  "stock": {
    "id": "000001.SZ",
    "name": "平安银行"
  },
  "opportunities": [
    {
      "opportunity_id": "uuid-1",
      "stock_id": "000001.SZ",
      "stock_name": "平安银行",
      "strategy_name": "momentum",
      "strategy_version": "1.0",
      
      // ===== Scanner 字段 =====
      "scan_date": "20251219",
      "trigger_date": "20251219",
      "trigger_price": 10.50,
      "trigger_conditions": {...},
      
      // ===== Simulator 添加的字段 =====
      "sell_date": "20251230",
      "sell_price": 11.20,
      "sell_reason": "take_profit",
      "price_return": 0.0667,
      "holding_days": 11,
      "max_price": 11.50,
      "min_price": 10.30,
      "max_drawdown": -0.019,
      
      "tracking": {
        "daily_prices": [10.50, 10.60, 10.55, ...],
        "daily_returns": [0, 0.0095, -0.0047, ...],
        "max_reached_date": "20251225",
        "min_reached_date": "20251222"
      },
      
      "status": "closed",
      "updated_at": "2025-12-19T15:00:00"
    }
  ],
  "summary": {
    "total_opportunities": 1,
    "total_closed": 1,
    "win_rate": 1.0,
    "avg_price_return": 0.0667,
    "avg_holding_days": 11,
    "annual_return": 1.52  // 年化收益率
  }
}
```

---

#### 3. Session Summary：`scan/{date}/summary.json`

```json
{
  "scan_date": "2025-12-19",
  "strategy_name": "momentum",
  "strategy_version": "1.0",
  
  "total_stocks_scanned": 1000,
  "total_opportunities_found": 50,
  "opportunity_rate": 0.05,
  
  "avg_expected_return": 0.08,
  "avg_confidence": 0.72,
  
  "top_opportunities": [
    {
      "stock_id": "000001.SZ",
      "stock_name": "平安银行",
      "expected_return": 0.15,
      "confidence": 0.85
    }
  ]
}
```

---

#### 4. Session Summary：`simulate/{session_id}/summary.json`

```json
{
  "session_id": "session_001",
  "session_date": "2025-12-19",
  "strategy_name": "momentum",
  "strategy_version": "1.0",
  
  // ===== 统计信息 =====
  "total_opportunities": 50,
  "total_closed": 50,
  "win_rate": 0.65,
  "avg_price_return": 0.05,
  "annual_return": 0.30,
  "avg_holding_days": 15,
  
  // ===== ROI 统计 =====
  "roi_mean": 0.05,
  "roi_median": 0.04,
  "roi_std": 0.08,
  "roi_min": -0.15,
  "roi_max": 0.20,
  
  // ===== 收益分布 =====
  "return_distribution": {
    "lt_-10pct": 2,
    "-10_to_-5pct": 5,
    "-5_to_0pct": 10,
    "0_to_5pct": 15,
    "5_to_10pct": 12,
    "10_to_15pct": 4,
    "gt_15pct": 2
  },
  
  // ===== 持有期分布 =====
  "duration_distribution": {
    "1_to_5_days": 5,
    "6_to_10_days": 10,
    "11_to_20_days": 25,
    "21_to_30_days": 8,
    "gt_30_days": 2
  }
}
```

---

## 执行流程

### Scanner 流程

```
1. StrategyManager (主进程)
   ↓
   discover_strategies()  # 发现用户策略
   ↓
   _load_global_cache()  # 加载全局缓存（股票列表、交易日历）
   ↓
   get_stock_list()  # 获取股票列表
   ↓
   _build_scan_jobs()  # 构建扫描作业
     job = {
       'stock_id': '000001.SZ',
       'execution_mode': 'scan',
       'strategy_name': 'momentum',
       'settings': {...},
       'scan_date': '20251219'
     }
   ↓
   ProcessWorker.execute(jobs)  # 多进程执行
   
2. BaseStrategyWorker (子进程)
   ↓
   __init__(job_payload)  # 初始化
   ↓
   process_entity()  # 处理单个股票
   ↓
   _execute_scan()
     ↓
     data_manager.load_latest_data(lookback=60)  # 加载最新数据
     ↓
     scan_opportunity()  # 用户实现（扫描逻辑）
       ↓
       分析最新数据
       ↓
       判断是否有买入信号
       ↓
       return Opportunity 或 None
   
3. StrategyManager (主进程)
   ↓
   collect_results()  # 收集结果
   ↓
   opportunity_service.save_scan_opportunities(opportunities)  # 保存到 JSON
   ↓
   generate_summary()  # 生成 summary.json
   ↓
   print("扫描完成：发现 50 个机会")
```

---

### Simulator 流程

```
1. StrategyManager (主进程)
   ↓
   _load_global_cache()  # 加载全局缓存
   ↓
   opportunity_service.load_scan_opportunities(date)  # 从 JSON 加载历史机会
   ↓
   session_manager.create_session()  # 创建新 session_id
   ↓
   _build_simulate_jobs()  # 构建模拟作业
     job = {
       'stock_id': '000001.SZ',
       'execution_mode': 'simulate',
       'strategy_name': 'momentum',
       'settings': {...},
       'opportunity': opportunity.to_dict(),
       'session_id': 'session_001',
       'end_date': '20251231'
     }
   ↓
   ProcessWorker.execute(jobs)  # 多进程执行
   
2. BaseStrategyWorker (子进程)
   ↓
   __init__(job_payload)  # 初始化
   ↓
   process_entity()  # 处理单个股票
   ↓
   _execute_simulate()
     ↓
     data_manager.load_historical_data(
       start_date=opportunity.trigger_date,
       end_date=end_date
     )  # 加载历史数据
     ↓
     simulate_opportunity(opportunity)  # 用户实现（回测逻辑）
       ↓
       遍历交易日
       ↓
       检查止盈止损
       ↓
       确定卖出日期和价格
       ↓
       计算价格收益率
       ↓
       return 更新后的 Opportunity
   
3. StrategyManager (主进程)
   ↓
   collect_results()  # 收集结果
   ↓
   opportunity_service.save_simulate_opportunities(opportunities, session_id)  # 保存到 JSON
   ↓
   generate_summary()  # 生成 summary.json
   ↓
   print("回测完成：胜率 65%，年化收益 30%")
```

---

## 与 Legacy 系统的关系

### Legacy 代码复用

**保留的组件**（直接复用或稍作调整）：

1. **数据加载**：
   - ✅ Legacy 的 DataManager
   - ✅ Legacy 的 K-line 加载逻辑
   - ✅ Legacy 的财务数据加载逻辑

2. **指标计算**：
   - ✅ Legacy 的 indicators.py
   - ✅ 各种技术指标计算

3. **JSON 存储逻辑**：
   - ✅ Legacy 的 JSON 读写逻辑
   - ✅ Summary 计算逻辑

4. **日期处理**：
   - ✅ Legacy 的 DateUtils
   - ✅ 交易日历处理

5. **实体对象**：
   - ✅ Legacy 的 Target, Opportunity, Investment 概念（调整）

---

### 主要变化

**新增或重构的组件**：

1. **StrategyManager**（新增）：
   - 类比 TagManager
   - 替代 Legacy 的 Analyzer

2. **BaseStrategyWorker**（新增）：
   - 类比 BaseTagWorker
   - 替代 Legacy 的 BaseStrategy
   - 职责更单一

3. **StrategyWorkerDataManager**（新增）：
   - 类比 TagWorkerDataManager
   - 负责数据加载和缓存

4. **Opportunity 对象**（重构）：
   - 合并 Legacy 的 Opportunity 和 Investment
   - 只关注价格变化（不涉及金额）

5. **文件组织**（改进）：
   - `tmp/` → `results/`
   - 分离 `scan/` 和 `simulate/`
   - 添加 `latest` 软链接

---

### 迁移策略

**Phase 1：保持兼容**
- ✅ 支持读取 Legacy 的 JSON 文件
- ✅ 新旧格式转换工具

**Phase 2：逐步迁移**
- ✅ 新策略使用新架构
- ✅ 旧策略继续使用 Legacy

**Phase 3：完全迁移**
- ✅ 所有策略迁移到新架构
- ✅ 删除 Legacy 代码

---

## 与 Tag 系统的对比

### 架构对比

| 维度 | Tag 系统 | Strategy 系统 |
|------|----------|---------------|
| **Manager** | TagManager | StrategyManager |
| **Worker** | BaseTagWorker | BaseStrategyWorker |
| **数据管理** | TagWorkerDataManager | StrategyWorkerDataManager |
| **作业负载** | entity_id + tag_definitions + settings | stock_id + execution_mode + settings |
| **处理方法** | process_entity() | process_entity() |
| **核心逻辑** | calculate_tag() | scan_opportunity() / simulate_opportunity() |
| **输出对象** | Dict (tag_id, value, date) | Opportunity |
| **存储** | 数据库表（tag_value） | JSON 文件 |
| **多进程** | ✅ ProcessWorker | ✅ ProcessWorker |
| **用户空间** | app/userspace/tags | app/userspace/strategies |

**相似度**：95%

---

### 核心差异

1. **Tag 系统**：
   - 单一核心逻辑（calculate_tag）
   - 输出简单（tag_id, value, date）
   - 只有计算逻辑
   - 数据库存储

2. **Strategy 系统**：
   - 双核心逻辑（scan_opportunity + simulate_opportunity）
   - 输出复杂（Opportunity 对象）
   - 包含扫描和回测
   - JSON 文件存储

---

### 成功经验复制

**从 Tag 系统学到的**：
1. ✅ Manager 负责发现和管理
2. ✅ Worker 负责执行逻辑（只在子进程实例化）
3. ✅ DataManager 负责数据加载
4. ✅ 使用字典序列化传递对象
5. ✅ 用户空间存放用户代码

**Strategy 系统的创新**：
1. ✅ 面向对象模型（Opportunity）
2. ✅ 双执行模式（Scanner + Simulator）
3. ✅ JSON 文件存储（直观易读）
4. ✅ Session 管理

---

## 未来扩展

### Portfolio 系统（TODO）

**职责**：
- 全局账户管理
- 资金分配（买多少）
- 凯莉公式
- 多策略协调
- 再平衡

**关键概念**：
```python
# 未来的 Portfolio 系统
class Portfolio:
    """组合管理系统（未来实现）"""
    
    def __init__(self, initial_cash: float):
        self.account = Account(initial_cash)  # 全局账户
        self.strategies = []
        self.positions = {}
    
    def add_strategy(self, strategy_name: str, allocation: float):
        """添加策略和资金分配"""
        pass
    
    def execute(self):
        """执行组合"""
        # 1. 扫描所有策略的机会
        # 2. 根据凯莉公式等计算买入金额
        # 3. 检查全局资金限制
        # 4. 执行交易
        # 5. 持有期管理
        # 6. 再平衡
        pass
```

**与当前系统的关系**：
- Opportunity → Investment（Portfolio 创建 Investment）
- 单股票分析 → 组合管理
- 价格收益率 → 实际盈亏

---

### Account 和 Investment 模型（TODO）

```python
@dataclass
class Account:
    """账户（未来实现）"""
    account_id: str
    initial_cash: float
    current_cash: float
    positions: Dict[str, Position]
    # ...

@dataclass
class Investment:
    """实际投资记录（未来实现）"""
    investment_id: str
    opportunity_id: str  # 关联的机会
    account_id: str
    buy_amount: int      # 实际买入数量
    buy_cost: float      # 实际买入成本
    profit: float        # 实际盈亏金额
    # ...
```

---

## 附录

### A. 用户实现示例

```python
# app/userspace/strategies/momentum/strategy_worker.py

from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from app.core.modules.strategy.models.opportunity import Opportunity
from typing import Optional
import uuid
from datetime import datetime


class MomentumStrategyWorker(BaseStrategyWorker):
    """动量策略 Worker"""
    
    def scan_opportunity(self) -> Optional[Opportunity]:
        """扫描动量机会"""
        # 1. 获取最新数据
        klines = self.data_manager.get_klines()
        
        if len(klines) < 60:
            return None
        
        # 2. 计算动量
        recent_avg = sum(k['close'] for k in klines[-20:]) / 20
        prev_avg = sum(k['close'] for k in klines[-60:-20]) / 40
        momentum = (recent_avg - prev_avg) / prev_avg
        
        # 3. 判断是否满足条件
        if momentum > 0.05:
            return Opportunity(
                opportunity_id=str(uuid.uuid4()),
                stock_id=self.stock_id,
                stock_name=klines[-1]['name'],
                strategy_name=self.strategy_name,
                strategy_version="1.0",
                scan_date=datetime.now().strftime('%Y%m%d'),
                trigger_date=klines[-1]['date'],
                trigger_price=klines[-1]['close'],
                trigger_conditions={'momentum': momentum},
                expected_return=momentum * 0.5,
                confidence=0.75,
                status='active',
                config_hash="abc123",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                metadata={}
            )
        
        return None
    
    def simulate_opportunity(self, opportunity: Opportunity) -> Opportunity:
        """回测动量机会"""
        # 1. 加载历史数据
        klines = self.data_manager.get_klines()
        
        # 2. 找到买入日期
        buy_index = next(i for i, k in enumerate(klines) if k['date'] == opportunity.trigger_date)
        buy_price = opportunity.trigger_price
        
        # 3. 遍历持有期
        sell_date = None
        sell_price = None
        sell_reason = None
        max_price = buy_price
        min_price = buy_price
        tracking_prices = []
        tracking_returns = []
        
        for i in range(buy_index, len(klines)):
            current_kline = klines[i]
            current_price = current_kline['close']
            
            tracking_prices.append(current_price)
            tracking_returns.append((current_price - buy_price) / buy_price)
            
            max_price = max(max_price, current_price)
            min_price = min(min_price, current_price)
            
            price_return = (current_price - buy_price) / buy_price
            
            # 止损
            if price_return < -0.05:
                sell_date = current_kline['date']
                sell_price = current_price
                sell_reason = 'stop_loss'
                break
            
            # 止盈
            if price_return > 0.10:
                sell_date = current_kline['date']
                sell_price = current_price
                sell_reason = 'take_profit'
                break
            
            # 最大持有期
            if i - buy_index >= 20:
                sell_date = current_kline['date']
                sell_price = current_price
                sell_reason = 'max_holding'
                break
        
        # 4. 如果没有触发，最后一天卖出
        if not sell_date:
            sell_date = klines[-1]['date']
            sell_price = klines[-1]['close']
            sell_reason = 'end_of_period'
        
        # 5. 更新 Opportunity
        opportunity.sell_date = sell_date
        opportunity.sell_price = sell_price
        opportunity.sell_reason = sell_reason
        opportunity.price_return = (sell_price - buy_price) / buy_price
        opportunity.holding_days = len(tracking_prices)
        opportunity.max_price = max_price
        opportunity.min_price = min_price
        opportunity.max_drawdown = (min_price - buy_price) / buy_price
        opportunity.tracking = {
            'daily_prices': tracking_prices,
            'daily_returns': tracking_returns
        }
        opportunity.status = 'closed'
        opportunity.updated_at = datetime.now().isoformat()
        
        return opportunity
```

---

### B. 配置示例

```python
# app/userspace/strategies/momentum/settings.py

settings = {
    "name": "momentum",
    "version": "1.0",
    "description": "动量策略",
    
    "core": {
        "entity_type": "stock",
        "start_date": "20240101",
        "end_date": "20241231"
    },
    
    "performance": {
        "max_workers": 8
    },
    
    "data_requirements": {
        "base_entity": "stock_kline_daily",
        "required_entities": []
    },
    
    "execution": {
        "stop_loss": -0.05,
        "take_profit": 0.10,
        "max_holding_days": 20
    },
    
    "params": {
        "momentum_threshold": 0.05,
        "lookback_days": 60
    }
}
```

---

## 版本历史

### v1.0 (2025-12-19)

**初始版本**：
- ✅ 完成核心架构设计
- ✅ 明确 Opportunity 为唯一核心对象
- ✅ 采用 JSON 文件存储
- ✅ 类比 Tag 系统的 Manager-Worker 架构
- ✅ 复用 Legacy 代码
- ✅ 为 Portfolio 系统预留接口

---

**文档结束**
