#!/usr/bin/env python3
# Scanner 模块设计文档

## 概述

Scanner 是 Strategy 模块中最简单的组件，负责：
1. **日期解析**：根据配置决定扫描日期（严格上一个交易日 vs 最新 K 线日期）
2. **机会扫描**：调用 `BaseStrategyWorker.scan_opportunity()` 获取机会
3. **结果缓存**：将扫描结果持久化到 CSV（最多保留 N 个交易日）
4. **Adapter 分发**：将机会分发给配置的 adapter（如 console、webhook 等）

---

## 核心设计

### 1. 日期解析策略

#### 1.1 严格模式（`use_strict_previous_trading_day = true`）
- **用途**：真实生产环境扫描
- **逻辑**：
  - 调用 `CalendarService.get_latest_completed_trading_date()` 获取最新已完成交易日
  - 查询该日期有 K 线的股票列表（`StockKlineModel.load_by_date(date)`）
  - 只扫描这些股票

#### 1.2 非严格模式（`use_strict_previous_trading_day = false`）
- **用途**：测试、数据不完整或收费受限场景
- **逻辑**：
  - 从 DB 查询 `SELECT MAX(date) FROM stock_kline WHERE term = 'daily'`
  - 查询该日期有 K 线的股票列表
  - 扫描这些股票

#### 1.3 实现：`ScanDateResolver`
```python
@dataclass
class ScanDateResolver:
    data_manager: DataManager
    
    def resolve_scan_date(
        self, 
        use_strict: bool
    ) -> tuple[str, list[str]]:
        """
        Returns:
            (scan_date, stock_ids): 扫描日期和股票列表
        """
```

---

### 2. 扫描结果缓存

#### 2.1 存储格式：CSV
- **路径**：`app/userspace/strategies/{strategy_name}/scan_cache/{date}/opportunities.csv`
- **字段**：与 `Opportunity` dataclass 对应（opportunity_id, stock_id, trigger_date, trigger_price, ...）
- **原因**：后续要换 DB，CSV 便于迁移

#### 2.2 缓存管理：`ScanCacheManager`
- **职责**：
  - 保存扫描结果到 CSV
  - 加载历史缓存（按日期）
  - 清理过期缓存（最多保留 `max_cache_days` 个交易日）
- **接口**：
  ```python
  @dataclass
  class ScanCacheManager:
      strategy_name: str
      max_cache_days: int = 10
      
      def save_opportunities(self, date: str, opportunities: list[Opportunity]) -> None
      def load_opportunities(self, date: str) -> list[Opportunity]
      def cleanup_old_cache(self) -> None
  ```

#### 2.3 缓存策略
- **保存时机**：每次扫描完成后立即保存
- **加载时机**：如果某日已缓存，可跳过扫描（可选，当前版本先不实现）
- **清理时机**：每次扫描前自动清理超过 `max_cache_days` 的旧缓存

---

### 3. Adapter 机制

#### 3.1 Adapter 接口
```python
class BaseOpportunityAdapter(ABC):
    """机会适配器基类（位于 core/modules/adapter/）"""
    
    def __init__(self, adapter_name: Optional[str] = None):
        """初始化 adapter，自动加载配置"""
        self.adapter_name = adapter_name or self._infer_adapter_name()
        self._config = self._load_config()  # 从 settings.py 加载
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项（支持点号分隔）"""
    
    @abstractmethod
    def process(
        self,
        opportunities: list[Opportunity],
        context: dict[str, Any]
    ) -> None:
        """
        处理机会列表（用户必须实现）
        
        Args:
            opportunities: 机会列表（已转换为 Opportunity dataclass）
            context: 上下文信息
                - date: 扫描日期
                - strategy_name: 策略名称
                - scan_summary: 扫描汇总统计
        """
    
    def log_info/warning/error(self, message: str) -> None:
        """日志记录方法"""
```

#### 3.2 Adapter 加载：`AdapterDispatcher`
- **加载路径**：`app.userspace.adapters.{adapter_name}`（全局共享，不在策略目录下）
- **查找规则**：查找继承 `BaseOpportunityAdapter` 的类
- **实例化**：无参数构造
- **配置**：每个 adapter 有自己的配置文件（在 `userspace/adapters/{adapter_name}/` 下）
- **调用时机**：Scanner 汇总完所有股票的机会后，一次性传入整天的机会列表
- **支持多个**：Scanner settings 中可以配置多个 adapter，会依次调用

#### 3.3 Console Adapter 示例
- **职责**：在 bash 中打印机会信息 + 历史胜率等统计
- **数据来源**：
  - 当前扫描机会：`opportunities` 参数
  - 历史模拟结果：读取 `results/simulations/price_factor/...` 或 `OpportunityService.load_simulate_opportunities(...)`
- **输出格式**：参考 legacy `BaseStrategy.report()` 和 `ResultAnalyzer.print_analysis_results()`

---

### 4. Scanner 主类

#### 4.1 类结构
```python
class Scanner:
    """扫描器主类"""
    
    def __init__(
        self,
        strategy_name: str,
        data_manager: DataManager,
        is_verbose: bool = False
    ):
        self.strategy_name = strategy_name
        self.data_manager = data_manager
        self.is_verbose = is_verbose
        
        # 加载配置
        self.settings = ScannerSettings.load_from_strategy_name(strategy_name)
        self.settings.validate_and_prepare()
        
        # 初始化组件
        self.date_resolver = ScanDateResolver(data_manager)
        self.cache_manager = ScanCacheManager(
            strategy_name=strategy_name,
            max_cache_days=self.settings.max_cache_days
        )
        self.adapter_dispatcher = AdapterDispatcher(strategy_name)
    
    def scan(self) -> dict[str, Any]:
        """
        执行扫描
        
        Returns:
            {
                'date': 扫描日期,
                'total_opportunities': 总机会数,
                'total_stocks': 扫描股票数,
                'summary': {...}
            }
        """
```

#### 4.2 扫描流程
1. **解析日期**：调用 `date_resolver.resolve_scan_date(...)`
2. **检查缓存**：可选，当前版本不实现跳过逻辑
3. **清理旧缓存**：`cache_manager.cleanup_old_cache()`
4. **多进程扫描**：
   - 构建 job list（每只股票一个 job）
   - 使用 `ProcessWorker` 并行执行
   - 每个子进程调用 `BaseStrategyWorker.scan_opportunity()`
5. **汇总结果**：收集所有股票的机会，转换为 `Opportunity` dataclass
6. **保存缓存**：`cache_manager.save_opportunities(date, opportunities)`
7. **调用 Adapter**：`adapter_dispatcher.dispatch(adapter_name, opportunities, context)`
8. **返回汇总**：返回扫描日期、机会数、汇总统计等

---

### 5. Settings 扩展

#### 5.1 ScannerSettings 新增字段
```python
@dataclass
class ScannerSettings(BaseSettings):
    # 新增字段
    _use_strict_previous_trading_day: Optional[bool] = None
    _max_cache_days: Optional[int] = None
    
    def _extract_scanner_fields(self) -> None:
        scanner_config = self.raw_settings.get("scanner", {})
        
        # use_strict_previous_trading_day（默认 true）
        self._use_strict_previous_trading_day = scanner_config.get(
            "use_strict_previous_trading_day", 
            True
        )
        
        # max_cache_days（默认 10）
        self._max_cache_days = scanner_config.get("max_cache_days", 10)
        if not isinstance(self._max_cache_days, int) or self._max_cache_days < 1:
            self._max_cache_days = 10
```

#### 5.2 Settings 配置示例
```python
# userspace/strategies/{strategy_name}/settings.py
settings = {
    "name": "example",
    "scanner": {
        "use_strict_previous_trading_day": True,  # 严格模式
        "max_cache_days": 10,  # 最多缓存 10 个交易日
        "adapters": ["console", "webhook"],  # 支持多个 adapter
        "max_workers": "auto"  # 已存在
    },
    # ...
}
```

#### 5.3 Adapter 目录结构
```
app/userspace/adapters/{adapter_name}/
├── __init__.py
├── adapter.py          # Adapter 实现（继承 BaseOpportunityAdapter）
└── settings.py         # Adapter 配置（包含 name 和用户自定义参数）
```

**示例**：
```python
# userspace/adapters/console/adapter.py
from app.core.modules.adapter import BaseOpportunityAdapter

class ConsoleAdapter(BaseOpportunityAdapter):
    def process(self, opportunities, context):
        # 使用 self.config 获取配置
        format = self.get_config('format', 'detailed')
        # 处理逻辑...
```

```python
# userspace/adapters/console/settings.py
settings = {
    "name": "console",  # 必须字段
    "format": "detailed",  # 用户自定义参数
    "show_history": True
}
```

---

## 文件结构

```
app/core/modules/
├── adapter/
│   ├── __init__.py
│   └── base_adapter.py         # BaseOpportunityAdapter 基类（独立模块）
└── strategy/
    └── components/
        └── scanner/
│   ├── __init__.py
│   ├── scanner.py              # Scanner 主类
│   ├── scan_date_resolver.py   # 日期解析器
│   ├── scan_cache_manager.py   # 缓存管理器
│   └── adapter_dispatcher.py   # Adapter 分发器
└── ...

app/core/modules/strategy/models/
└── opportunity.py              # Opportunity dataclass（已存在）

app/userspace/
├── adapters/                    # 全局共享的 adapters
│   ├── console/
│   │   ├── __init__.py
│   │   ├── adapter.py           # Console adapter 实现
│   │   └── config.py            # Console adapter 配置（可选）
│   └── webhook/
│       ├── __init__.py
│       ├── adapter.py
│       └── config.py
└── strategies/{strategy_name}/
    └── scan_cache/
        └── {date}/
            └── opportunities.csv
```

---

## 实施计划（已完成 ✅）

### Phase 1：基础设施
1. [x] 扩展 `ScannerSettings`：添加 `use_strict_previous_trading_day` 和 `max_cache_days`
2. [x] 实现 `ScanDateResolver`：日期解析逻辑
3. [x] 实现 `ScanCacheManager`：CSV 缓存读写 + 清理

### Phase 2：Adapter 机制
4. [x] 定义 `BaseOpportunityAdapter` 接口（位于 `app/core/modules/adapter/`）
5. [x] 实现 `AdapterDispatcher`：动态加载 userspace adapter
6. [x] 实现 `ConsoleAdapter` 示例：打印机会 + 历史统计
7. [x] 实现 `HistoryLoader`：加载历史模拟结果并计算统计

### Phase 3：Scanner 主类
8. [x] 实现 `Scanner` 主类：整合所有组件
9. [x] 多进程扫描：复用 `ProcessWorker` + `BaseStrategyWorker.scan_opportunity()`
10. [x] Adapter 验证：在 ScannerSettings 中验证 adapter 是否可用
11. [x] 默认输出：当所有 adapter 失败时使用默认输出

---

## 注意事项

1. **日期解析**：strict 模式必须使用 `CalendarService.get_latest_completed_trading_date()`，不能直接用 `MAX(date)`
2. **缓存格式**：使用 CSV，字段与 `Opportunity` dataclass 对齐，便于后续迁移到 DB
3. **Adapter 加载**：从 userspace 加载，与 hooks 机制类似，但更简单（无参数构造）
4. **多进程安全**：Scanner Worker 在子进程内创建，不会 pickle 问题（与 PriceFactorSimulator 一致）
5. **错误处理**：日期解析失败、adapter 加载失败等场景要有明确的日志和降级策略
