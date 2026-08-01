# New Tea Quant 代码风格规范

> 最后更新：2026-06-30
> 适用范围：core/infra, core/modules

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
  - [8.4 test_cases.yaml 测试注册表](#84-test_casesyaml-测试注册表)
- [9. 文档规范](#9-文档规范)
- [10. 导入规范](#10-导入规范)
- [11. 版本管理规范](#11-版本管理规范)
- [12. 注释规范](#12-注释规范)

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

### 1.3 模块命名和暴露规范

**模块命名规范：**

| 文件类型 | 命名规范 | 示例 | 说明 |
|---------|---------|------|------|
| 模块主文件 | 模块名.py | `discovery.py`, `project_context.py` | 对外暴露API |
| 内部实现文件夹 | `core/` | `core/file_manager.py`, `core/config_manager.py` | 不要使用 `_impl/`, `modules/` |
| 根目录文件 | 只保留必需文件 | `discovery.py`, `api.yaml`, `module_info.yaml`, `glossary.yaml`, `__init__.py` | 不保留冗余文件 |

**API命名规范：**

| 命名方式 | 规范 | 示例 | 说明 |
|---------|------|------|------|
| namespace API | 使用嵌套结构 | `Discovery.file.xxx`, `ProjectContext.path.xxx` | 提供namespace分组 |
| Facade类命名 | 简洁直观 | `Discovery`, `ProjectContext` | 单一对外入口 |
| 不暴露内部class | 不导出实现类 | 不暴露 `FileUtils`, `ConfigManager` | 保持内部私有 |
| 不暴露便捷函数 | 不导出便捷方法 | 不暴露 `find_file`, `load_json` | 使用namespace API代替 |

**示例：**
```python
# ✅ 推荐：模块命名和暴露方式
discovery/
├── discovery.py          # 模块主文件（对外API）
├── core/                 # 内部实现目录（不要用_impl/）
│   ├── file_manager.py
│   └── config_manager.py
├── api.yaml
├── module_info.yaml
├── glossary.yaml
└── __init__.py          # 只导出 Discovery

# __init__.py
from .discovery import Discovery

__all__ = ['Discovery']  # 只导出Facade类

# 使用示例
from discovery import Discovery

file_path = Discovery.file.find_file("config.yaml")  # namespace API
project_root = Discovery.path.get_root()

# ❌ 禁止：错误的命名和暴露
discovery/
├── _impl/               # ❌ 不要用 _impl/
├── modules/             # ❌ 不要用 modules/
├── file_utils.py        # ❌ 不要暴露内部实现
└── __init__.py
    # ❌ 导出内部类
    from .file_utils import FileUtils
    from .config_manager import ConfigManager

    # ❌ 导出便捷函数
    def find_file(filename):
        return FileUtils.find_file(filename)

    __all__ = ['Discovery', 'FileUtils', 'ConfigManager', 'find_file']
```

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
from core.infra.db import DatabaseManager
from core.infra.utils.utils import Utils

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

类 docstring 一句话说明职责；只有非显而易见的约束才补充一句。

```python
class CalendarService:
    """交易日历查询与缓存。"""

    def __init__(self, data_manager: DataManager):
        super().__init__(data_manager)
        self._trade_calendar = data_manager.get_table("sys_trade_calendar")

    def get_latest_completed_trading_date(self) -> str:
        """返回最新已完成交易日（YYYYMMDD）。"""
        pass
```

**不写：** 使用示例、`Args`/`Returns` 复述签名、方法列表（对外 API 见 `api.yaml` / `OVERVIEW.md`）。

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

### 5.1 Facade模式要求

**核心原则：**
- **只暴露一个Facade类**：模块对外只提供一个主要类作为入口
- **不暴露内部实现**：内部Manager、Utils、Helper类不对外导出
- **不暴露便捷函数**：不提供平铺的便捷方法，使用namespace API代替

**示例：**
```python
# ✅ 推荐：Facade模式
class Discovery:
    """
    项目发现服务 - Facade类

    对外唯一入口，提供namespace API
    """

    def __init__(self):
        self._file_manager = FileManager()      # 内部实现，不对外暴露
        self._config_manager = ConfigManager()  # 内部实现，不对外暴露

    @property
    def file(self) -> FileNamespace:
        """文件相关API namespace"""
        return FileNamespace(self._file_manager)

    @property
    def path(self) -> PathNamespace:
        """路径相关API namespace"""
        return PathNamespace(self._file_manager)

# __init__.py
from .discovery import Discovery

__all__ = ['Discovery']  # 只导出Facade类

# ❌ 禁止：暴露多个类和便捷函数
class FileUtils:  # ❌ 不应该对外暴露
    """内部实现类"""
    pass

class ConfigManager:  # ❌ 不应该对外暴露
    """内部实现类"""
    pass

def find_file(filename):  # ❌ 不应该暴露便捷函数
    """便捷函数"""
    return FileUtils.find_file(filename)

__all__ = ['Discovery', 'FileUtils', 'ConfigManager', 'find_file']
```

### 5.2 Namespace API设计

**namespace分组原则：**
- **功能分组**：按功能域分组（如 file, path, config）
- **嵌套结构**：使用property提供namespace入口
- **命名清晰**：namespace名称直观表达功能域

**示例：**
```python
# ✅ 推荐：namespace API设计
class Discovery:
    """Facade类"""

    @property
    def file(self) -> FileNamespace:
        """文件相关操作"""
        return FileNamespace(self._file_manager)

    @property
    def path(self) -> PathNamespace:
        """路径相关操作"""
        return PathNamespace(self._file_manager)

class FileNamespace:
    """文件namespace"""

    def find_file(self, filename: str) -> Path:
        """查找文件"""
        return self._manager.find_file(filename)

    def load_json(self, path: Path) -> dict:
        """加载JSON文件"""
        return self._manager.load_json(path)

# 使用示例
from discovery import Discovery

# 使用namespace API
file_path = Discovery.file.find_file("config.yaml")  # 清晰的namespace结构
config = Discovery.file.load_json(file_path)
project_root = Discovery.path.get_root()

# ❌ 禁止：平铺API
class Discovery:
    def find_file(self, filename):  # ❌ 不使用平铺API
        pass

    def load_json(self, path):      # ❌ 不使用平铺API
        pass

# 使用平铺API（混乱）
file_path = Discovery().find_file("config.yaml")  # ❌ 不直观
config = Discovery().load_json(file_path)
```

### 5.3 不保留向后兼容proxy

**原则：**
- **0.x版本直接改动**：开发阶段允许颠覆性改动
- **不保留旧API proxy**：不提供向后兼容的代理函数
- **不保留类名alias**：不使用alias保留旧类名

**示例：**
```python
# ✅ 推荐：0.x版本直接改动
# 旧版本 0.3.0
# find_file("config.yaml")  # 平铺API

# 新版本 0.4.0
# Discovery.file.find_file("config.yaml")  # namespace API

# 直接删除旧API，不保留proxy
__all__ = ['Discovery']  # 只导出新API

# ❌ 禁止：保留向后兼容proxy
def find_file(*args, **kwargs):
    """已废弃，请使用 Discovery.file.find_file"""
    warnings.warn("find_file is deprecated, use Discovery.file.find_file")
    return Discovery.file.find_file(*args, **kwargs)

# ❌ 禁止：保留旧类名alias
FileUtils = Discovery  # 不允许alias
ConfigFinder = Discovery  # 不允许alias
```

### 5.4 函数签名规范

```python
def fetch_stock_data(
    stock_id: str,
    start_date: str,
    end_date: str,
    *,
    include_adjusted: bool = True,
    cache_enabled: bool = False,
) -> pd.DataFrame:
    """按日期区间拉取股票 K 线（含可选复权）。"""
    pass
```

**规范要点：**
- 必选参数在前，可选参数在后
- 必选参数后加 `*,` 强制使用关键字参数
- 类型注解必须完整
- docstring 说明「做什么」；签名和类型已表达的信息不必重复

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
      binding: instance
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
      binding: instance
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
      binding: static
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
| `binding` | enum | 方法绑定方式：`static` / `class` / `instance` | ✅ 必需 |
| `parameters` | list | 参数列表（带注释） | ✅ 必需 |
| `returns` | type | 返回值类型（带注释） | ✅ 必需 |
| `throws` | list | 异常列表 | ✅ 必需 |
| `example` | string | 使用示例 | ✅ 必需 |

**binding 取值说明：**

| 值 | 含义 | 典型用法 |
|----|------|---------|
| `static` | 静态方法或类命名空间函数 | `@staticmethod`、`Class.method()` |
| `class` | 类方法 | `@classmethod` |
| `instance` | 实例方法 | `self.method()` |

> 历史字段 `is_static` 已废弃，请改用 `binding`。迁移：`is_static: true` → `binding: static`；`is_static: false` → `binding: instance`（若为 `@classmethod` 则用 `class`）。

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
- **集成测试**：测试模块间交互（业务模块 `__test__`；核心模块保持纯单元测试）

### 8.4 test_cases.yaml 测试注册表

核心模块推荐在 `__test__/test_cases.yaml` 维护测试索引，作为 UT 的单一事实来源：

```yaml
cases:
  - id: 1
    case: api
    description: "公开 API 与 Mode 枚举"
    file: test_api.py
    scenarios:
      - id: 1
        name: test_facade_export
        description: "..."
```

**规则：**
- 一个 `case` 对应一个大类，通常映射一个 `test_*.py` 文件
- `scenarios[].name` 与 pytest 函数名一致
- 无对应 test 文件的 case 可不写 `file`（仅文档/手工 case）
- 不要测其他层职责（如 `MachineInfo` 属于 `core/infra`，不应出现在 engine 的 case 里）

**参考：** `core/modules/backtest_engine/__test__/test_cases.yaml`

---

## 8A. 调度模块：performance 与 dispatch 配置

适用于 `backtest_engine` 及类似调度 Facade。

| 层级 | 职责 | 示例 |
|------|------|------|
| Engine | base defaults + dataclass validate/resolve | `EntityBasedPerformance.base().merge(...).validate()` |
| 应用模块 | 性能基准调优配置（用户不可改） | `tag/settings/dispatch.yaml` |
| 用户 settings | 业务字段 only | `update_mode`、`run_options.dry_run` |

**禁止：**
- `settings["performance"]` 传入 engine
- engine 读取 global `worker.json` dispatch 段
- 模块内 re-export infra 空壳（`from core.infra.x import Y` 单独成文件）

**进度：**
- engine 内统一计算；`enable_progress_display` 只控制 CMD 输出
- slice 细粒度 unit 通过 payload hook 回调 engine reporter

---


### 9.1 文档字符串

**原则：** 说清楚「做什么」即可。函数名、参数名、类型注解、返回值类型已经表达的信息，不要在 docstring 里再写一遍。

| 写 | 不写 |
|----|------|
| 一句话职责 / 行为 | `Args` / `Returns` 复述签名 |
| 非显而易见的约束、算法要点 | `Examples` / 用法示例 |
| 仅在异常含义不直观时写 `Raises` | 对外 API 的完整契约（见 `api.yaml`） |

```python
def calculate_return(prices: pd.Series, method: str = "simple") -> pd.Series:
    """计算收益率序列（支持 simple / log）。"""
    pass


def resolve_for_planning(performance: dict, capacity: MachineCapacity) -> dict:
    """将 performance 中的 auto 字段解析为具体数值，供 planner 使用。"""
    pass
```

内部实现函数：同上，保持简短。**不要**在代码里写 usage example。

### 9.2 类文档

与函数相同：类 docstring 一句话说明职责；公开 Facade 的用法与参数见 `api.yaml`、模块 `OVERVIEW.md`。

```python
class BacktestEngine:
    """回测调度 Facade：entity_based / slice_based 两种执行模式。"""

    @staticmethod
    def run(mode: str, jobs: list, execute_fn: ExecuteFn, **kwargs) -> RunResult:
        """按 mode 分发到 entity_based 或 slice_based pipeline。"""
        ...
```

### 9.3 模块文档

**核心模块（`core/modules/*`）：** 根目录 `OVERVIEW.md`（使用者入门）+ `docs/ARCHITECTURE.md` / `docs/DECISIONS.md` + `api.yaml`。不强制 `README.md`。

**其他模块：** 可按需保留简短 `README.md` 或 `OVERVIEW.md`，指向 `api.yaml`。

---

## 10. 导入规范

### 10.1 导入原则

1. **优先绝对导入**
   ```python
   # ✅ 推荐
   from core.infra.db import DatabaseManager

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

4. **禁止 re-export 空壳**
   ```python
   # ✅ 直接使用 infra
   from core.infra.machine_capacity import MachineInfo

   # ❌ 模块内仅做转发的空壳文件
   # core/modules/foo/core/shared/machine_info.py
   from core.infra.machine_capacity import MachineInfo  # 仅此一行 — 应删除，调用方直引 infra
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
from core.infra.db import DatabaseManager
from core.infra.utils.utils import Utils
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
- [ ] 公开类/方法有一句 docstring（说明做什么，不重复签名）
- [ ] 不在代码里写 Examples；对外契约在 `api.yaml`
- [ ] 复杂逻辑有行内/块注释说明

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

---

## 11. 版本管理规范

### 11.1 版本号更新规则

**版本号格式：**
- 遵循语义化版本规范：`MAJOR.MINOR.PATCH`
- 格式示例：`0.4.1`, `1.0.0`, `2.3.5`

**更新规则：**

| 变更类型 | 是否更新版本号 | 示例 | 说明 |
|---------|---------------|------|------|
| 小改动（修复bug、优化代码） | ❌ 不更新 | 修复文档错误、优化性能 | 不影响API |
| 分支没变（同一开发分支） | ❌ 不更新 | 同一分支上的多次提交 | 未发布新版本 |
| 中版本变化（新增功能、重构API） | ✅ 更新 | 0.3.0 → 0.4.0 | MINOR版本增加 |
| 大版本变化（架构变更） | ✅ 更新 | 0.4.0 → 1.0.0 | MAJOR版本增加 |
| 补丁版本（修复bug） | ✅ 更新 | 0.4.0 → 0.4.1 | PATCH版本增加（已发布版本） |

### 11.2 版本号更新时机

**何时更新版本号：**
- ✅ 新功能发布时
- ✅ API重构时
- ✅ 架构变更时
- ✅ 已发布版本修复bug时

**何时不更新版本号：**
- ❌ 开发过程中的小改动
- ❌ 同一分支的多次提交
- ❌ 文档更新
- ❌ 代码优化（不影响功能）

### 11.3 0.x版本兼容性规则

**开发阶段规则：**
- 0.x版本表示开发阶段
- ✅ 可以颠覆性改动
- ✅ 直接删除旧API
- ✅ 不保留向后兼容
- ⚠️ 1.x版本开始需要向后兼容

**示例：**
```python
# ✅ 推荐：0.x版本直接改动
# 旧版本 0.3.0
# find_file("config.yaml")  # 平铺API

# 新版本 0.4.0
# Discovery.file.find_file("config.yaml")  # namespace API

# 直接删除旧API，不保留proxy

# ⚠️ 1.x版本需要向后兼容
# 旧版本 1.0.0
# find_file("config.yaml")

# 新版本 1.1.0
# Discovery.file.find_file("config.yaml")

# 保留旧API，添加废弃警告
def find_file(*args, **kwargs):
    """已废弃，请使用 Discovery.file.find_file"""
    warnings.warn("find_file is deprecated, use Discovery.file.find_file", DeprecationWarning)
    return Discovery.file.find_file(*args, **kwargs)
```

---

## 12. 注释规范

### 12.1 注释原则

**核心原则：**
- **简洁必要**：只保留必要的注释
- **避免冗余**：不重复已在文档中说明的内容
- **解释复杂逻辑**：注释复杂算法和特殊处理

### 12.2 注释分类规则

| 注释类型 | 是否保留 | 说明 | 示例 |
|---------|---------|------|------|
| 复杂逻辑注释 | ✅ 保留 | 解释复杂算法、特殊处理逻辑 | 解释为什么使用对数加权 |
| 模块文档 | ✅ 保留 | 模块级别的说明 | 模块功能、依赖关系 |
| 类文档 | ✅ 保留 | 类职责、使用方式 | 类的主要功能 |
| 函数文档 | ✅ 保留 | 简短功能说明 | 函数的主要目的 |
| 冗余参数注释（Args） | ❌ 删除 | 参数已在api.yaml中说明 | 参数类型和说明 |
| 冗余返回值注释（Returns） | ❌ 删除 | 返回值已在api.yaml中说明 | 返回值类型和说明 |
| 冗余示例注释（Examples） | ❌ 删除 | 示例已在api.yaml中提供 | 使用示例 |
| 冗余注意事项（Note） | ❌ 删除 | 注意事项应在文档中说明 | 使用注意 |
| 行内注释 | ⚠️ 谨慎使用 | 仅解释复杂逻辑 | 解释特殊处理 |

### 12.3 注释示例

**✅ 推荐：简洁必要的注释**
```python
def calculate_weighted_average(prices: List[float], weights: List[float]) -> float:
    """
    计算加权平均值
    """
    # 使用对数加权避免数值溢出（复杂逻辑需要注释）
    log_weights = np.log(weights + 1e-10)
    return np.sum(prices * np.exp(log_weights)) / np.sum(np.exp(log_weights))

def find_file(filename: str) -> Path:
    """
    查找文件
    """
    return self._file_manager.find_file(filename)
```

**❌ 禁止：冗余注释**
```python
def find_file(filename: str) -> Path:
    """
    查找文件

    Args:
        filename: 文件名  # ❌ 冗余，已在 api.yaml 中说明

    Returns:
        文件路径  # ❌ 冗余，已在 api.yaml 中说明

    Examples:  # ❌ 冗余，已在 api.yaml 中提供
        >>> find_file("config.yaml")
        /path/to/config.yaml

    Note:  # ❌ 冗余，应在文档中说明
        该函数会递归搜索
    """
    return self._file_manager.find_file(filename)
```

### 12.4 文档位置规则

**文档职责分离：**

| 文档位置 | 内容 | 示例 |
|---------|------|------|
| `api.yaml` | 对外 API：签名、参数、返回值、异常、示例 | Facade 契约 |
| `OVERVIEW.md` | 使用者快速入门 | 集成示例、边界说明 |
| `docs/ARCHITECTURE.md` | 架构与目录 | 维护者 |
| 代码 docstring | 一句话说明做什么；非显而易见的行为 | 内部 helper |

**避免重复：**
- ❌ docstring 里写 `Args`/`Returns`/`Examples` 复述签名或 `api.yaml`
- ✅ 类型注解 + 命名自解释时，docstring 可仅一行
- ✅ 行内注释只解释复杂逻辑

---