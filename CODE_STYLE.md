# New Tea Quant 代码风格规范

> 最后更新：2026-06-26
> 适用范围：core/infra, core/modules, core/utils

---

## 目录

- [1. 命名规范](#1-命名规范)
- [2. 架构层次设计](#2-架构层次设计)
- [3. 代码组织](#3-代码组织)
- [4. 类的设计原则](#4-类的设计原则)
- [5. API 设计规范](#5-api-设计规范)
- [6. API 契约规范](#6-api-契约规范)
- [7. 错误处理](#7-错误处理)
- [8. 测试规范](#8-测试规范)
- [9. 文档规范](#9-文档规范)
- [10. 导入规范](#10-导入规范)

---

## 1. 命名规范

### 1.1 基本原则

- **清晰优于简洁**：函数名和变量名应该自解释
- **一致优于个性**：整个项目保持统一的命名风格
- **英语命名**：所有代码、注释、文档使用英文（中文仅用于面向用户的提示信息）

### 1.2 变量命名

| 类型 | 规范 | 示例 | 说明 |
|------|------|------|------|
| 普通变量 | snake_case | `user_name`, `stock_count` | 小写+下划线 |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` | 全大写+下划线 |
| 类名 | PascalCase | `CalendarService`, `DatabaseManager` | 每个单词首字母大写 |
| 模块/包名 | snake_case | `data_manager`, `calendar_service` | 小写+下划线 |
| 私有属性/方法 | _snake_case | `_internal_cache`, `_validate_input()` | 单下划线前缀 |
| 保护属性/方法 | __snake_case | `__secret_key` | 双下划线前缀（避免使用，Python名称修饰会导致问题） |

### 1.3 函数命名规范

#### 1.3.1 数据转换/组装/解析

```python
# 数据格式转换（to_xxx）
def to_dict(obj) -> dict:
    """转换为字典"""
    pass

def to_dataframe(data) -> pd.DataFrame:
    """转换为DataFrame"""
    pass

# 数据解析（from_xxx，与to_xxx对应）
def from_dict(data: dict) -> BacktestConfig:
    """从字典解析为配置对象"""
    pass

def from_json_string(json_str: str) -> dict:
    """从JSON字符串解析为字典"""
    pass

# 复杂格式/类解析（parse_xxx）
def parse_config_file(path: str) -> dict:
    """解析配置文件（处理文件读取、格式验证等）"""
    pass

def parse_database_url(url: str) -> DatabaseConfig:
    """解析数据库URL为配置对象"""
    pass

def parse_backtest_result(raw_data: bytes) -> BacktestResult:
    """解析回测结果数据（处理反序列化、字段映射等）"""
    pass

# 数据组装（构建复杂对象）
def build_query_params(filters: dict) -> dict:
    """组装查询参数"""
    pass

def assemble_report_data(raw_data: dict) -> ReportData:
    """组装报表数据"""
    pass
```

**命名规范对比：**
| 场景 | 前缀 | 示例 | 说明 |
|------|------|------|------|
| 格式转换 | `to_xxx` | `to_dict()` | 简单的格式转换 |
| 格式解析 | `from_xxx` | `from_dict()` | 简单的反向转换，与`to_xxx`对应 |
| 复杂解析 | `parse_xxx` | `parse_config_file()` | 复杂格式、多步骤解析、涉及验证和映射 |
| 数据组装 | `build_xxx` / `assemble_xxx` | `build_query_params()` | 从多个数据源组装复杂对象 |

#### 1.3.2 数据/逻辑验证
```python
# 布尔验证（返回 True/False）
def is_valid_stock_id(stock_id: str) -> bool:
    """验证股票ID格式是否有效"""
    pass

def is_trading_day(date: str) -> bool:
    """判断是否为交易日"""
    pass

# 抛异常验证（验证失败抛出异常）
def validate_config(config: dict) -> None:
    """验证配置，失败抛出 ValueError"""
    pass

def validate_schema(data: dict, schema: dict) -> None:
    """验证数据结构，失败抛出 ValidationError"""
    pass
```

#### 1.3.3 数据获取
```python
# 从外部API请求
def fetch_stock_price(stock_id: str) -> float:
    """从第三方API获取股价"""
    pass

def send_request_to_exchange(params: dict) -> dict:
    """发送请求到交易所"""
    pass

# 从数据库/文件加载
def load_trade_calendar() -> List[str]:
    """从数据库加载交易日历"""
    pass

def save_backtest_result(result: dict) -> None:
    """保存回测结果到数据库"""
    pass

# 从内存/缓存获取
def get_latest_price(stock_id: str) -> float:
    """从缓存获取最新价格"""
    pass

def set_config(key: str, value: Any) -> None:
    """设置配置"""
    pass
```

#### 1.3.4 异步操作
```python
# 异步操作统一后缀 _async
async def fetch_data_async(url: str) -> dict:
    """异步获取数据"""
    pass

async def save_result_async(data: dict) -> None:
    """异步保存结果"""
    pass
```

#### 1.3.5 逻辑分支（复杂条件判断）
```python
# 简单逻辑：直接在代码中判断
if stock_id.startswith('6'):
    # 处理上交所股票

# 复杂逻辑：提取为函数
def is_shanghai_stock(stock_id: str) -> bool:
    """判断是否为上交所股票（6开头）"""
    return stock_id.startswith('6')

def is_valid_backtest_period(start_date: str, end_date: str) -> bool:
    """验证回测区间是否有效（起止日期合法且区间内有交易日）"""
    pass

# 使用
if is_shanghai_stock(stock_id):
    # 处理上交所股票
```

---

## 2. 架构层次设计

### 2.1 编排层 vs 实施层

项目采用**双层次架构设计**，明确区分流程控制和具体实现：

#### 编排层（Orchestration Layer）

**角色类比：车间经理**

- **职责**：流程管控、资源协调、异常处理
- **关注点**：可读性、业务逻辑清晰度
- **调试场景**：业务流程错误、状态不一致、资源调度问题
- **命名特征**：`run_xxx`, `execute_xxx`, `process_xxx`, `flow_xxx`

```python
class BacktestOrchestrator:
    """
    回测编排器 - 管理整个回测流程
    
    职责：
        - 协调数据加载、策略执行、结果分析等步骤
        - 处理异常和状态转换
        - 记录流程日志
    
    不负责：
        - 具体的数据加载算法
        - 策略的具体计算逻辑
    """
    
    def run_backtest(self, strategy_name: str) -> BacktestResult:
        """编排完整的回测流程"""
        # 1. 加载配置
        config = self._load_config(strategy_name)
        
        # 2. 加载历史数据（调用实施层）
        data_loader = DataLoader(config)
        historical_data = data_loader.load_data()
        
        # 3. 执行回测（调用实施层）
        engine = BacktestEngine(config)
        result = engine.execute(historical_data)
        
        # 4. 分析结果（调用实施层）
        analyzer = ResultAnalyzer()
        report = analyzer.generate_report(result)
        
        return report
```

#### 实施层（Implementation Layer）

**角色类比：工人**

- **职责**：具体计算、数据处理、算法实现
- **关注点**：计算准确性、算法效率、单元测试覆盖
- **调试场景**：算法错误、计算精度问题、性能瓶颈
- **命名特征**：具体功能命名，如 `calculate_xxx`, `filter_xxx`, `normalize_xxx`

```python
class BacktestEngine:
    """
    回测引擎 - 具体执行策略回测
    
    职责：
        - 应用策略逻辑计算买卖信号
        - 计算持仓、收益、风险指标
        - 处理具体的数值计算
    
    不负责：
        - 数据加载流程
        - 结果展示和分析
    """
    
    def execute(self, historical_data: pd.DataFrame) -> dict:
        """执行回测计算（纯计算逻辑）"""
        # 具体的计算实现
        signals = self._calculate_signals(historical_data)
        positions = self._simulate_positions(signals)
        returns = self._calculate_returns(positions)
        
        return {
            'signals': signals,
            'positions': positions,
            'returns': returns
        }
    
    def _calculate_signals(self, data: pd.DataFrame) -> np.ndarray:
        """计算交易信号（具体算法）"""
        # 纯数学计算，便于单元测试
        pass
```

### 2.2 层次划分原则

| 判断维度 | 编排层 | 实施层 |
|---------|--------|--------|
| **代码行数** | 通常10-50行，调用多个实施层 | 可较长，专注单一计算 |
| **函数调用** | 调用多个实施层方法 | 不调用编排层，可调用其他实施层 |
| **返回值** | 通常返回复杂对象/结果 | 返回具体计算结果 |
| **异常处理** | 捕获并转换异常 | 抛出具体异常 |
| **日志** | 记录流程节点 | 记录计算细节（可选） |
| **测试重点** | 集成测试、流程测试 | 单元测试、算法验证 |

### 2.3 代码示例对比

**错误的设计（混合编排和实施）：**

```python
# ❌ 不推荐：编排层包含具体计算逻辑
class BacktestManager:
    def run_backtest(self, strategy_name: str):
        config = self._load_config(strategy_name)
        
        # 具体数据加载逻辑混在编排流程中
        db = DatabaseManager()
        query = f"SELECT * FROM stock_kline WHERE stock_id IN ({stock_ids})"
        data = pd.read_sql(query, db.engine)
        
        # 具体计算逻辑混在编排流程中
        signals = []
        for date in data['date'].unique():
            day_data = data[data['date'] == date]
            signal = self._calculate_signal(day_data)  # 具体算法
            signals.append(signal)
        
        # 流程继续...
```

**正确的设计（清晰分层）：**

```python
# ✅ 推荐：编排层专注流程
class BacktestOrchestrator:
    def run_backtest(self, strategy_name: str):
        config = self._load_config(strategy_name)
        
        # 调用实施层：数据加载
        loader = DataLoader(config)
        data = loader.load_historical_data()
        
        # 调用实施层：策略执行
        engine = BacktestEngine(config)
        result = engine.execute(data)
        
        # 调用实施层：结果分析
        analyzer = ResultAnalyzer()
        report = analyzer.analyze(result)
        
        return report

# ✅ 推荐：实施层专注计算
class DataLoader:
    def load_historical_data(self) -> pd.DataFrame:
        """具体的数据加载实现"""
        db = DatabaseManager()
        query = self._build_query(self.config.stock_ids)
        return pd.read_sql(query, db.engine)

class BacktestEngine:
    def execute(self, data: pd.DataFrame) -> dict:
        """具体的回测计算"""
        signals = self._calculate_all_signals(data)
        return self._simulate_trading(signals)
```

### 2.4 模块文件组织

```
module_name/
├── orchestrator.py        # 编排层（流程管理）
├── loader.py              # 实施层（数据加载）
├── engine.py              # 实施层（核心计算）
├── analyzer.py            # 实施层（结果分析）
└── utils.py               # 实施层（辅助计算）
```

**命名约定：**
- 编排层文件：`orchestrator.py`, `manager.py`, `coordinator.py`, `flow.py`
- 实施层文件：`engine.py`, `loader.py`, `analyzer.py`, `calculator.py`, `processor.py`

---

## 3. 代码组织

### 3.1 模块结构

每个模块应遵循以下标准结构：

```
module_name/
├── __test__/              # 单元测试（必须）
│   ├── __init__.py
│   ├── test_xxx.py
│   └── test_yyy.py
├── docs/                  # 文档（推荐）
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── DESIGN.md
├── sub_module_1/          # 子模块
│   ├── __init__.py
│   └── ...
├── __init__.py            # 模块初始化
├── main_file.py           # 主要业务代码
├── helper.py              # 辅助函数
├── constants.py           # 常量定义
├── types.py               # 类型定义
└── README.md              # 模块说明
```

### 3.2 文件职责划分

| 文件名 | 职责 | 示例内容 |
|--------|------|----------|
| `service.py` | 业务服务类 | `CalendarService`, `StockService` |
| `manager.py` | 管理器类 | `DatabaseManager`, `ConfigManager` |
| `utils.py` / `helpers.py` | 工具函数 | `Utils.deep_merge()`, `format_date()` |
| `constants.py` | 常量定义 | `MAX_RETRY = 3`, `DEFAULT_TIMEOUT = 30` |
| `types.py` | 类型定义 | `TypedDict`, `NamedTuple`, 自定义类型 |
| `models.py` | 数据模型 | `@dataclass`, `pydantic.BaseModel` |
| `exceptions.py` | 自定义异常 | `class ValidationError(Exception)` |

### 3.3 导入顺序

```python
# 1. 标准库
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 2. 第三方库
import numpy as np
import pandas as pd

# 3. 本项目内部模块（绝对导入）
from core.infra.db.db_manager import DatabaseManager
from core.utils.utils import Utils

# 4. 相对导入（仅在包内部使用）
from .constants import MAX_RETRY
from .types import BacktestResult
```

**规则：**
- 每组导入之间空一行
- 组内按字母顺序排列
- 优先使用绝对导入
- 避免使用 `from xxx import *`

---

## 4. 类的设计原则

### 4.1 类的选择指南

| 场景 | 推荐方式 | 示例 | 说明 |
|------|---------|------|------|
| **业务服务** | 实例类 + 依赖注入 | `CalendarService(data_manager)` | 有状态，需要依赖 |
| **管理器/协调器** | 单例（谨慎使用） | `DatabaseManager` | 全局唯一，生命周期等同于进程 |
| **工具函数集合** | 静态方法类 | `Utils.deep_merge()` | 无状态，逻辑分组 |
| **数据模型** | `@dataclass` 或 Pydantic | `BacktestConfig` | 纯数据容器 |
| **抽象基类** | ABC + `@abstractmethod` | `BaseLoader` | 定义接口规范 |

### 4.2 类的文档模板

```python
class CalendarService:
    """
    日历服务 - 封装交易日相关的查询和缓存

    职责：
        - 提供交易日查询接口
        - 缓存交易日历数据
        - 计算交易日期区间

    使用方式：
        >>> calendar = CalendarService(data_manager)
        >>> latest_date = calendar.get_latest_completed_trading_date()
        >>> is_trading = calendar.is_trading_day("20240101")

    对外 API：
        - get_latest_completed_trading_date(): 获取最新已完成交易日
        - is_trading_day(date): 判断是否为交易日
    """

    def __init__(self, data_manager: DataManager):
        """
        初始化日历服务

        Args:
            data_manager: 数据管理器实例
        """
        super().__init__(data_manager)
        self._trade_calendar = data_manager.get_table("sys_trade_calendar")

    def get_latest_completed_trading_date(self) -> str:
        """
        获取最新已完成交易日

        Returns:
            交易日期字符串（YYYYMMDD格式）

        Raises:
            ValueError: 无法获取交易日历时抛出
        """
        pass
```

### 4.3 类的构造方式

#### 3.3.1 依赖注入（推荐）
```python
class StockService:
    def __init__(self, data_manager: DataManager, cache: Cache):
        self._data_manager = data_manager
        self._cache = cache
```

**优点：**
- 易于测试（可注入mock）
- 生命周期由调用方管理
- 依赖关系显式

#### 3.3.2 全局单例（谨慎使用）
```python
class DatabaseManager:
    _instance = None

    @classmethod
    def get_default(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

**适用场景：**
- 数据库连接池
- 配置管理器
- 日志管理器

**注意：** 单例常驻内存，仅在真正需要全局状态时使用。

---

## 5. API 设计规范

### 5.1 函数签名规范

```python
def fetch_stock_data(
    stock_id: str,
    start_date: str,
    end_date: str,
    *,
    include_adjusted: bool = True,
    cache_enabled: bool = False,
) -> pd.DataFrame:
    """
    获取股票数据

    Args:
        stock_id: 股票代码（如 '000001.SZ'）
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        include_adjusted: 是否包含复权数据
        cache_enabled: 是否启用缓存

    Returns:
        股票数据 DataFrame，包含 open, high, low, close, volume 列

    Raises:
        ValueError: 日期格式错误或股票代码无效
        DataNotFoundError: 数据不存在
    """
    pass
```

**规范要点：**
- 必选参数在前，可选参数在后
- 必选参数后加 `*,` 强制使用关键字参数
- 类型注解必须完整
- 文档字符串包含 Args, Returns, Raises

### 5.2 返回值规范

#### 4.2.1 单一数据
```python
def get_stock_name(stock_id: str) -> str:
    """返回股票名称"""
    return "平安银行"
```

#### 4.2.2 多个数据
```python
def get_stock_info(stock_id: str) -> Dict[str, Any]:
    """返回股票信息字典"""
    return {
        "stock_id": "000001.SZ",
        "name": "平安银行",
        "industry": "银行",
    }

# 或使用 TypedDict
class StockInfo(TypedDict):
    stock_id: str
    name: str
    industry: str

def get_stock_info(stock_id: str) -> StockInfo:
    pass
```

#### 4.2.3 可能失败的操作
```python
# 方式1: 抛出异常
def fetch_data(url: str) -> dict:
    """获取数据，失败抛出异常"""
    if not url:
        raise ValueError("URL不能为空")
    return requests.get(url).json()

# 方式2: 返回 None
def find_stock(stock_id: str) -> Optional[Stock]:
    """查找股票，不存在返回 None"""
    pass

# 方式3: 返回结果对象
@dataclass
class FetchResult:
    success: bool
    data: Optional[dict]
    error: Optional[str]

def fetch_data_safe(url: str) -> FetchResult:
    """安全获取数据"""
    try:
        data = requests.get(url).json()
        return FetchResult(success=True, data=data, error=None)
    except Exception as e:
        return FetchResult(success=False, data=None, error=str(e))
```

---

## 6. API 契约规范

### 6.1 API契约文件定义

每个模块必须在根目录包含 `api.yaml`，定义所有公开API：

**文件结构：**
```
module_name/
├── module_info.yaml      # 模块元数据（名称、版本、依赖）
├── api.yaml              # API契约定义（签名、参数、返回值、异常）
├── api_test/             # API测试目录（优先级高于UT）
├── __test__/             # 单元测试目录
└── docs/
    └── API.md            # 详细文档（使用说明、最佳实践）
```

**职责分离：**
- `module_info.yaml`：模块元数据（name, version, dependencies）
- `api.yaml`：API契约（签名、参数、返回值、异常、测试要求）
- `docs/API.md`：详细文档（使用说明、最佳实践、示例）

### 6.2 api.yaml 文件格式

```yaml
# API Contract - infra.project_context
# Version: 0.3.1
# Last Updated: 2026-06-26
#
# 目的：
#   - 为所有API建立快捷目录
#   - 让开发者和自动测试一目了然
#   - 用户知道有哪些API和怎么用
#   - 测试知道有哪些对外接口和用法，快速覆盖

module: infra.project_context
version: 0.3.1

---

ProjectContextManager:
  layer: orchestrator
  description: "Facade，组合各Manager提供统一入口"

  apis:
    core_info():
      description: "获取 core meta 信息"
      stability: stable
      is_static: false
      parameters:
        - "无参数"
      returns: Optional[Dict[str, Any]]
      throws: []
      example: |
        ctx = ProjectContextManager()
        info = ctx.core_info()
        # {"version": "0.4.1", "release_date": "2026-06-26"}

    core_version():
      description: "获取 core 版本号"
      stability: stable
      is_static: false
      parameters:
        - "无参数"
      returns: Optional[str]
      throws: []
      example: |
        ctx = ProjectContextManager()
        version = ctx.core_version()  # "0.4.1"

---

PathManager:
  layer: implementation
  description: "路径管理器 - 提供项目常用路径的快捷访问"

  apis:
    get_root():
      description: "获取项目根目录的绝对路径"
      stability: stable
      is_static: true
      parameters:
        - "无参数"
      returns: Path
      throws: []
      example: |
        root = PathManager.get_root()  # /path/to/new-tea-quant

---

# API稳定性分级定义
api_stability_levels:
  stable:
    description: "API稳定，不会轻易修改"
    breaking_change_risk: low

  beta:
    description: "API可能调整，但会提前通知"
    breaking_change_risk: medium

  experimental:
    description: "API可能随时修改，仅供实验"
    breaking_change_risk: high

  deprecated:
    description: "API已废弃，将在未来版本删除"
    breaking_change_risk: high
```

### 6.3 API定义字段说明

**核心字段（每个API必须包含）：**

| 字段 | 类型 | 说明 | 是否必需 |
|------|------|------|---------|
| `description` | string | API功能描述 | ✅ 必需 |
| `stability` | enum | API稳定性级别（stable/beta/experimental/deprecated） | ✅ 必需 |
| `is_static` | bool | 是否静态方法 | ✅ 必需 |
| `parameters` | list | 参数列表（带注释） | ✅ 必需 |
| `returns` | type | 返回值类型（带注释） | ✅ 必需 |
| `throws` | list | 异常列表 | ✅ 必需 |
| `example` | string | 使用示例 | ✅ 必需 |

**可选字段（根据需要添加）：**

| 字段 | 类型 | 说明 | 使用场景 |
|------|------|------|---------|
| `environment_dependencies` | list | 环境变量依赖 | 有环境变量依赖时添加 |

**类级别字段：**

| 字段 | 类型 | 说明 | 是否必需 |
|------|------|------|---------|
| `layer` | enum | 层次（orchestrator/implementation） | ✅ 必需 |
| `description` | string | 类描述 | ✅ 必需 |

### 6.4 参数格式定义

**无参数：**
```yaml
parameters:
  - "无参数"
```

**有参数：**
```yaml
parameters:
  - default_path: Path  # 默认配置文件路径
  - user_path: Path  # 用户配置文件路径（可选）
  - deep_merge_fields: Optional[Set[str]] = None  # 深度合并字段
```

**参数格式规范：**
- 格式：`name: type = default_value  # comment`
- 默认值：可选参数必须标注默认值（`= None`, `= "json"`）
- 注释：每个参数必须添加简短注释

### 6.5 异常格式定义

**无异常：**
```yaml
throws: []
```

**有异常：**
```yaml
throws:
  - type: ValueError
    condition: "domain包含非法路径（如'..')"
  - type: OverridableConfigNotFoundError
    condition: "core和userspace均未找到配置"
```

### 6.6 API稳定性分级

| 级别 | 描述 | 使用场景 | Breaking Change风险 |
|------|------|---------|-------------------|
| `stable` | API稳定，不会轻易修改 | 已验证的核心API | 低 |
| `beta` | API可能调整，但会提前通知 | 新功能测试阶段 | 中 |
| `experimental` | API可能随时修改，仅供实验 | 实验性功能 | 高 |
| `deprecated` | API已废弃，将在未来版本删除 | 旧API，保留向后兼容 | 高 |

### 6.7 API测试覆盖要求

**测试优先级：**
```
API测试 > UT测试
```

**API测试必须覆盖：**
1. API签名正确性
2. 参数验证（正常、边界、非法）
3. 返回值类型和格式
4. 异常处理（预期异常、未预期异常）
5. 使用示例验证

**测试目录结构：**
```
module_name/
├── api_test/                    # API测试（优先级高于UT）
│   ├── __init__.py
│   ├── test_api_class1.py
│   ├── test_api_class2.py
│   └── api_test_runner.py      # 基于api.yaml自动生成测试
├── __test__/                    # 单元测试
│   ├── test_class1.py
│   └── test_class2.py
```

---

## 7. 错误处理

### 7.1 自定义异常类

```python
# exceptions.py
class NewTeaQuantError(Exception):
    """New Tea Quant 基础异常"""
    pass

class ValidationError(NewTeaQuantError):
    """数据验证错误"""
    pass

class DataNotFoundError(NewTeaQuantError):
    """数据不存在错误"""
    pass

class ConfigurationError(NewTeaQuantError):
    """配置错误"""
    pass

class BacktestError(NewTeaQuantError):
    """回测错误"""
    pass
```

### 7.2 异常使用规范

```python
# ✅ 推荐：使用具体的异常类型
def validate_stock_id(stock_id: str) -> None:
    if not stock_id:
        raise ValidationError("股票代码不能为空")
    if not stock_id.endswith(('.SZ', '.SH')):
        raise ValidationError(f"无效的股票代码格式: {stock_id}")

# ✅ 推荐：提供上下文信息
def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise ConfigurationError(f"配置文件不存在: {path}")
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"配置文件格式错误: {path}, {e}")

# ❌ 避免：裸异常和过于宽泛的异常捕获
try:
    do_something()
except:  # 太宽泛
    pass

# ✅ 推荐：捕获具体异常
try:
    data = fetch_data(url)
except requests.Timeout:
    logger.error(f"请求超时: {url}")
    raise
except requests.RequestException as e:
    logger.error(f"请求失败: {url}, {e}")
    raise DataNotFoundError(f"无法获取数据: {url}") from e
```

### 7.3 错误日志规范

```python
import logging

logger = logging.getLogger(__name__)

def process_data(data: dict) -> None:
    try:
        validate_data(data)
        save_data(data)
    except ValidationError as e:
        logger.warning(f"数据验证失败: {e}")
        raise
    except Exception as e:
        logger.error(f"处理数据失败: {e}", exc_info=True)
        raise
```

---

## 8. 测试规范

### 8.1 测试文件组织

```
module_name/
├── __test__/
│   ├── __init__.py
│   ├── test_service.py          # 测试 service.py
│   ├── test_manager.py           # 测试 manager.py
│   ├── test_integration.py      # 集成测试
│   └── test_fixtures.py         # 测试固件
```

### 8.2 测试命名规范

```python
# 测试文件：test_calendar_service.py
import pytest
from core.modules.data_manager.data_services.calendar.calendar_service import CalendarService

class TestCalendarService:
    """日历服务测试"""

    def test_get_latest_trading_date_success(self):
        """测试获取最新交易日 - 成功场景"""
        pass

    def test_get_latest_trading_date_empty_calendar(self):
        """测试获取最新交易日 - 日历为空"""
        pass

    def test_is_trading_day_with_valid_date(self):
        """测试判断交易日 - 有效日期"""
        pass

    def test_is_trading_day_with_weekend(self):
        """测试判断交易日 - 周末"""
        pass

    def test_is_trading_day_with_invalid_format(self):
        """测试判断交易日 - 日期格式错误"""
        with pytest.raises(ValueError):
            self.service.is_trading_day("2024-01-01")
```

### 8.3 测试覆盖要求

- **单元测试**：覆盖所有公开方法
- **边界测试**：测试边界条件（空值、极值、非法值）
- **异常测试**：测试所有异常分支
- **集成测试**：测试模块间交互

---

## 9. 文档规范

### 9.1 文档字符串格式

使用 Google 风格的文档字符串：

```python
def calculate_return(
    prices: pd.Series,
    method: str = "simple"
) -> pd.Series:
    """
    计算收益率

    支持简单收益率和对数收益率两种计算方法。

    Args:
        prices: 价格序列（必须为正数）
        method: 计算方法，可选 'simple' 或 'log'
            - 'simple': 简单收益率 = (P_t - P_{t-1}) / P_{t-1}
            - 'log': 对数收益率 = ln(P_t / P_{t-1})

    Returns:
        收益率序列，第一个值为 NaN

    Raises:
        ValueError: prices 包含非正数或 method 参数无效

    Examples:
        >>> prices = pd.Series([100, 105, 103])
        >>> returns = calculate_return(prices)
        >>> returns[1]
        0.05

        >>> returns = calculate_return(prices, method='log')
        >>> round(returns[1], 4)
        0.0488
    """
    pass
```

### 9.2 类文档模板

```python
class BacktestEngine:
    """
    回测引擎 - 执行策略回测的核心组件

    职责：
        - 加载历史数据
        - 执行交易策略
        - 计算绩效指标
        - 生成回测报告

    使用方式：
        >>> config = BacktestConfig(...)
        >>> engine = BacktestEngine(config)
        >>> result = engine.run(strategy)
        >>> report = engine.generate_report()

    对外 API：
        - run(strategy): 执行回测
        - generate_report(): 生成报告
        - get_performance(): 获取绩效指标

    注意：
        - 单线程执行，不支持并发
        - 需要先调用 initialize() 方法
    """

    def __init__(self, config: BacktestConfig):
        """
        初始化回测引擎

        Args:
            config: 回测配置对象

        Raises:
            ConfigurationError: 配置参数无效
        """
        pass
```

### 9.3 模块文档

每个模块根目录应包含 `README.md`：

```markdown
# Calendar Service

## 概述
日历服务提供交易日历相关功能。

## 主要功能
- 获取最新交易日
- 判断交易日
- 计算交易日区间

## 使用示例
```python
from core.modules.data_manager.data_services.calendar import CalendarService

calendar = CalendarService(data_manager)
latest_date = calendar.get_latest_completed_trading_date()
```

## API 文档
详见 [API.md](./docs/API.md)
```

---

## 10. 导入规范

### 10.1 导入原则

1. **优先绝对导入**
   ```python
   # ✅ 推荐
   from core.infra.db.db_manager import DatabaseManager

   # ❌ 避免
   from ..db.db_manager import DatabaseManager
   ```

2. **避免循环导入**
   - 使用延迟导入（在函数内部导入）
   - 重构模块结构，提取公共部分

3. **按需导入重型库**
   ```python
   # ✅ 推荐：在需要时导入
   def process_dataframe(data):
       import pandas as pd  # 只在此函数内使用
       df = pd.DataFrame(data)
       return df

   # ❌ 避免：顶层导入不常用的库
   import pandas as pd  # 如果模块大部分函数不需要
   ```

### 10.2 导入顺序示例

```python
"""
模块文档字符串
"""

# 1. 标准库
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 2. 第三方库
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# 3. 本项目内部模块
from core.infra.db.db_manager import DatabaseManager
from core.utils.utils import Utils
from core.exceptions import ValidationError

# 4. 常量和类型定义
from .constants import MAX_RETRY, DEFAULT_TIMEOUT
from .types import BacktestResult, StockInfo

# 模块级常量
MODULE_VERSION = "1.0.0"
DEFAULT_CONFIG = {"timeout": 30}

# 模块级 logger
logger = logging.getLogger(__name__)
```

---

## 附录：代码审查清单

在提交代码前，请确认以下清单：

### 命名
- [ ] 变量、函数、类命名符合规范
- [ ] 函数名清晰表达意图
- [ ] 避免使用缩写（除非广泛认可的如 id, url）

### 结构
- [ ] 文件组织符合模块结构规范
- [ ] 类的职责单一
- [ ] 函数长度不超过 50 行（复杂逻辑除外）

### 文档
- [ ] 类和公开方法有文档字符串
- [ ] 文档字符串包含 Args, Returns, Raises
- [ ] 复杂逻辑有注释说明

### 测试
- [ ] 单元测试覆盖公开方法
- [ ] 测试命名清晰
- [ ] 边界条件有测试

### 错误处理
- [ ] 使用自定义异常类
- [ ] 异常信息提供上下文
- [ ] 关键操作有日志

### 类型注解
- [ ] 函数参数和返回值有类型注解
- [ ] 使用 Optional 表示可能为 None 的返回值
- [ ] 复杂类型使用 TypedDict 或 NamedTuple

---

## 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0 | 2026-06-26 | 初始版本 |