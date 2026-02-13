# Adapter 模块架构文档

**版本：** 3.0  
**最后更新**: 2026-01-17

---

## 目录

- [业务目标](#业务目标)
- [设计目标](#设计目标)
- [设计理念](#设计理念)
- [核心组件详解](#核心组件详解)
- [架构图](#架构图)
- [运行时 Workflow](#运行时-workflow)
- [未来扩展方向](#未来扩展方向)

---

## 业务目标

Adapter 模块是策略扫描结果的后续处理层，提供统一的场所让用户自定义后续处理逻辑。

**重要说明**：
- 本模块**仅提供场所**，不涉及任何交易功能
- **本模块尚未实现**，以下为概念设计

### 核心职责

Adapter 模块有 3 个核心职责：

1. **提供自定义场地**：给用户提供自定义下一步处理的场地（`userspace/adapters/`）
2. **自动加载模拟结果**：根据 opportunity 的股票信息和 strategy 信息，批量查找模拟结果（如果用户配置了的话）
3. **传递数据给 Action**：把 opportunity 对象（以及可选的模拟结果）传递给用户自定义的 action

### 架构分层

- **Core 模块**（`core/modules/adapter/`）：
  - 提供基类和工具
  - 负责根据 opportunity 的股票信息和 strategy 信息，批量查找模拟结果
  - 将 opportunity 和模拟结果（可选）传递给用户的 action

- **Userspace 模块**（`userspace/adapters/`）：
  - 用户自定义的 action
  - 接收 opportunity 对象和模拟结果（可选）
  - 实现后续处理逻辑（如发送通知、数据分析、对接第三方系统等）
---

## 设计目标

基于上述业务目标，我们制定了以下技术设计目标：

1. **提供自定义场地**：通过基类 + 继承的方式，支持用户自定义 action
2. **自动加载模拟结果**：Core 模块的 adapter 负责批量查找模拟结果，用户可配置是否加载
3. **数据传递**：将 opportunity 对象和模拟结果（可选）传递给用户的 action
4. **动态加载**：支持从 `userspace/adapters/` 动态加载 action，无需修改核心代码
5. **配置驱动**：支持配置是否加载模拟结果，以及传递哪些数据给 action

---

## 设计理念

### 1. 分层设计

- **Core 模块**：负责批量查找模拟结果，将数据传递给 action
- **Userspace 模块**：用户自定义的 action，实现后续处理逻辑
- 两者通过统一的接口连接，保持解耦

### 2. 接口抽象

通过基类定义统一的接口：
- Core 模块的 adapter 负责数据准备（查找模拟结果）
- Userspace 的 action 负责业务处理（接收数据并处理）
- 接口统一，便于扩展

### 3. 配置驱动

支持配置：
- 是否加载模拟结果（可选）
- 传递哪些数据给 action（只传 opportunity，或同时传 opportunity + 模拟结果）
- 每个 action 可以有自己的配置文件

### 4. 容错设计

- 如果模拟结果查找失败，可以选择只传递 opportunity
- 如果某个 action 加载失败，跳过并继续处理其他 action
- 如果某个 action 处理失败，记录错误并继续处理其他 action

---

## 核心组件详解

### Core 模块 Adapter（批量查找模拟结果）

**职责**：
- ✅ 根据 opportunity 的股票信息和 strategy 信息，批量查找模拟结果
- ✅ 将 opportunity 对象和模拟结果（可选）传递给用户的 action
- ✅ 支持配置是否加载模拟结果
- ✅ 支持配置传递哪些数据给 action

**不负责**：
- ❌ 不负责实现具体的业务处理逻辑（由用户的 action 负责）
- ❌ 不负责加载 action（由 `AdapterDispatcher` 负责）

### BaseOpportunityAdapter（基类）

**职责**：
- ✅ 定义 action 接口（`process` 抽象方法）
- ✅ 提供配置加载（从 `userspace/adapters/{action_name}/settings.py`）
- ✅ 提供配置访问方法（`config` 属性、`get_config` 方法）
- ✅ 提供日志记录方法（`log_info`, `log_warning`, `log_error`）
- ✅ 自动推断 action 名称（从类名）

**不负责**：
- ❌ 不负责加载模拟结果（由 Core 模块的 adapter 负责）
- ❌ 不负责加载 action（由 `AdapterDispatcher` 负责）
- ❌ 不负责验证 action（由 `AdapterValidator` 负责）

**关键方法**：

```python
@abstractmethod
def process(
    self,
    opportunities: List[Opportunity],
    context: Dict[str, Any]
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
```

### 用户自定义 Action（Userspace）

**职责**：
- ✅ 接收 opportunity 对象和模拟结果（可选）
- ✅ 实现后续处理逻辑（如发送通知、数据分析、对接第三方系统等）
- ✅ 通过继承 `BaseOpportunityAdapter` 实现 `process` 方法

**不负责**：
- ❌ 不负责查找模拟结果（由 Core 模块的 adapter 负责）
- ❌ 不负责加载数据（由 Core 模块的 adapter 负责）

**注意**：Action 是用户自定义的组件，放在 `userspace/adapters/` 下，框架不提供任何交易相关功能。

**关键方法**：

```python
@staticmethod
def load_stock_history(
    strategy_name: str,
    stock_id: str
) -> Optional[Dict[str, Any]]:
    """
    加载单只股票的历史模拟统计
    
    Returns:
        统计信息字典，如果不存在返回 None
        {
            'win_rate': 0.65,  # 胜率
            'avg_return': 0.05,  # 平均收益率
            'total_investments': 10,  # 总投资次数
            'win_count': 7,  # 盈利次数
            'loss_count': 3,  # 亏损次数
            'max_return': 0.15,  # 最大收益
            'min_return': -0.08,  # 最小收益
            'avg_holding_days': 5.2  # 平均持有天数
        }
    """
```

### AdapterValidator（验证器）

**职责**：
- ✅ 验证 adapter 是否存在且可用
- ✅ 检查 adapter 是否继承 `BaseOpportunityAdapter`
- ✅ 检查 adapter 是否实现 `process` 方法
- ✅ 尝试实例化 adapter（验证构造是否正常）

**不负责**：
- ❌ 不负责加载 adapter（由 `AdapterDispatcher` 负责）
- ❌ 不负责调用 adapter（由 `AdapterDispatcher` 负责）

**关键方法**：

```python
def validate_adapter(adapter_name: str) -> Tuple[bool, str]:
    """
    验证 adapter 是否可用
    
    Returns:
        (is_valid, error_message): 
            - is_valid: True 表示可用，False 表示不可用
            - error_message: 如果不可用，返回错误信息；如果可用，返回空字符串
    """
```

### AdapterDispatcher（分发器，位于 Strategy 模块）

**职责**：
- ✅ 从 `userspace/adapters/{adapter_name}/adapter.py` 动态加载 adapter 类
- ✅ 实例化 adapter（无参数构造）
- ✅ 调用 adapter 的 `process` 方法
- ✅ 处理 adapter 加载失败和调用失败的情况
- ✅ 如果所有 adapter 都失败，使用默认输出

**不负责**：
- ❌ 不负责定义 adapter 接口（由 `BaseOpportunityAdapter` 负责）
- ❌ 不负责验证 adapter（由 `AdapterValidator` 负责）

**关键方法**：

```python
def dispatch(
    self,
    adapter_names: List[str],
    opportunities: List[Opportunity],
    context: dict[str, Any]
) -> None:
    """
    分发机会到指定的 adapters（支持多个）
    
    如果所有 adapter 都失败，会使用默认输出。
    """
```

---

## 架构图

### 整体架构
```
┌─────────────────────────────────────────────────────────────┐
│                    Strategy 模块                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Scanner                                  │  │
│  │  - 扫描股票，发现机会                                 │  │
│  │  - 汇总统计                                           │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         AdapterDispatcher                            │  │
│  │  - 调用 Core Adapter                                 │  │
│  │  - 加载用户 Action                                   │  │
│  └──────────────────┬───────────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│          Adapter 模块 (Core)                                │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      Core Adapter                                    │  │
│  │  - 根据 opportunity 的股票信息和 strategy 信息      │  │
│  │  - 批量查找模拟结果（如果配置了）                    │  │
│  │  - 将 opportunity + 模拟结果传递给用户的 Action     │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                      │                                        │
│                      │ 传递数据                               │
│                      ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      BaseOpportunityAdapter (基类)                    │  │
│  │  - 定义接口 (process)                                │  │
│  │  - 配置加载                                           │  │
│  │  - 日志记录                                           │  │
│  └──────────────────┬───────────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      │ 用户实现
                      ▼
┌─────────────────────────────────────────────────────────────┐
│          Adapter 模块 (Userspace)                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  console/    │  │  notification/│  │  custom/     │     │
│  │  action.py   │  │  action.py   │  │  action.py   │     │
│  │  settings.py │  │  settings.py │  │  settings.py │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  (示例：输出到控制台)  (用户自定义)    (用户自定义)        │
│                                                             │
│  用户自定义的 Action：                                      │
│  - 接收 opportunity 对象和模拟结果（可选）                  │
│  - 实现后续处理逻辑（发送通知、数据分析等）                │
└─────────────────────────────────────────────────────────────┘
```

### 组件关系

```
BaseOpportunityAdapter (基类)
    │
    ├─▶ 提供配置加载
    │   └─▶ 从 userspace/adapters/{adapter_name}/settings.py 加载
    │
    ├─▶ 提供日志方法
    │   └─▶ log_info, log_warning, log_error
    │
    └─▶ 定义接口
        └─▶ process(opportunities, context) (抽象方法)

HistoryLoader (工具类)
    │
    ├─▶ 加载历史统计
    │   └─▶ 从 PriceFactorSimulator 结果中读取
    │
    └─▶ 计算统计信息
        └─▶ 胜率、平均收益、持有天数等

AdapterValidator (验证器)
    │
    ├─▶ 验证 adapter 是否存在
    │
    ├─▶ 验证 adapter 是否继承 BaseOpportunityAdapter
    │
    └─▶ 验证 adapter 是否实现 process 方法

AdapterDispatcher (分发器，Strategy 模块)
    │
    ├─▶ 动态加载 adapter 类
    │   └─▶ 从 userspace/adapters/{adapter_name}/adapter.py
    │
    ├─▶ 实例化 adapter
    │   └─▶ adapter = adapter_class()
    │
    └─▶ 调用 adapter.process()
        └─▶ adapter.process(opportunities, context)
```

---

## 运行时 Workflow

### Adapter 处理流程

```
1. Scanner 扫描完成
   │
   ├─▶ 汇总统计信息
   │
   └─▶ 构建 context
       {
           'date': scan_date,
           'strategy_name': strategy_name,
           'scan_summary': summary
       }
       │
       ▼
2. AdapterDispatcher.dispatch()
   │
   ├─▶ 读取配置的 action_names (如 ["console", "notification"])
   │
   ├─▶ Core Adapter 处理
   │   │
   │   ├─▶ 根据 opportunity 的股票信息和 strategy 信息
   │   │   └─▶ 批量查找模拟结果（如果配置了）
   │   │       └─▶ 从数据库查找历史模拟结果
   │   │
   │   └─▶ 准备数据
   │       └─▶ opportunity 对象 + 模拟结果（可选）
   │
   ├─▶ 遍历每个 action_name
   │   │
   │   ├─▶ 加载 action 类
   │   │   └─▶ _load_action_class(action_name)
   │   │       │
   │   │       ├─▶ 尝试导入模块
   │   │       │   └─▶ importlib.import_module(
   │   │       │       f"userspace.adapters.{action_name}.action"
   │   │       │   )
   │   │       │
   │   │       ├─▶ 查找继承 BaseOpportunityAdapter 的类
   │   │       │   └─▶ inspect.getmembers(module)
   │   │       │
   │   │       └─▶ 返回 action 类
   │   │
   │   ├─▶ 实例化 action
   │   │   └─▶ action = action_class()
   │   │       │
   │   │       └─▶ BaseOpportunityAdapter.__init__()
   │   │           │
   │   │           ├─▶ 推断 action_name
   │   │           │
   │   │           └─▶ 加载配置
   │   │               └─▶ _load_config()
   │   │                   └─▶ 从 userspace/adapters/{action_name}/settings.py
   │   │
   │   └─▶ 调用 action.process()
   │       └─▶ action.process(opportunities, simulation_results, context)
   │           │
   │           └─▶ 用户实现的处理逻辑
   │               - 输出到控制台（console action 示例）
   │               - 发送通知
   │               - 数据分析
   │               - 对接第三方系统
   │               - 等等（用户自定义）
   │
   └─▶ 如果所有 action 都失败
       └─▶ 记录错误日志
```

### 配置加载流程

```
BaseOpportunityAdapter.__init__()
    │
    └─▶ _load_config()
        │
        ├─▶ 构建模块路径
        │   └─▶ f"userspace.adapters.{adapter_name}.settings"
        │
        ├─▶ 尝试导入 settings 模块
        │   └─▶ importlib.import_module(module_path)
        │
        ├─▶ 查找 settings 或 config 字典
        │   ├─▶ 如果存在 settings.settings → 使用
        │   ├─▶ 如果存在 settings.config → 使用
        │   └─▶ 否则 → 使用空字典 {}
        │
        └─▶ 存储到 self._config
```

---

## 实现状态

**注意**：本模块**尚未实现**，以上为概念设计。当前代码中的 `BaseOpportunityAdapter` 和 `HistoryLoader` 是早期实现，将在模块正式实现时进行重构。

## 未来扩展方向

### 待实现扩展（单机版支持）

1. **Core Adapter 实现**：实现批量查找模拟结果的功能
2. **配置支持**：支持配置是否加载模拟结果，以及传递哪些数据给 action
3. **Action 优先级**：支持为 action 设置优先级，按优先级顺序执行
4. **Action 条件执行**：支持根据条件决定是否执行某个 action（如只在特定日期执行）

### 可扩展方向（单机版不支持）

1. **分布式 Action**：支持将 action 部署到不同机器，通过消息队列分发
2. **Action 插件市场**：支持从插件市场安装 action，无需手动创建

---

## 相关文档

- **[overview.md](./overview.md)**：模块概览和快速入门
- **[decisions.md](./decisions.md)**：重要决策记录

---

**文档结束**
