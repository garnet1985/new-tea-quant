# Adapter 模块概览

> **快速入门指南**：本文档提供 Adapter 模块的快速概览和基本使用方式。详细的设计理念和架构说明请参考 [architecture.md](./architecture.md)。

---

## 模块简介

**Adapter 模块**是策略扫描结果的后续处理层，提供一个统一的场所让用户自定义处理逻辑。

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
  - 负责根据 opportunity 的股票信息和 strategy 信息，批量查找模拟结果
  - 将 opportunity 和模拟结果（可选）传递给用户的 action

- **Userspace 模块**（`userspace/adapters/`）：
  - 用户自定义的 action
  - 接收 opportunity 对象和模拟结果（可选）
  - 实现后续处理逻辑（如发送通知、数据分析、对接第三方系统等）

### 核心特性

- **可扩展性**：用户可以通过继承 `BaseOpportunityAdapter` 创建自定义 adapter
- **动态加载**：支持从 `userspace/adapters/` 动态加载 adapter
- **多适配器支持**：可以同时配置多个 adapter 处理同一批机会
- **配置驱动**：每个 adapter 可以有自己的配置文件（`settings.py`）
- **历史统计**：提供 `HistoryLoader` 工具，可以加载历史模拟结果用于展示

### 核心概念

| 概念 | 说明 |
|------|------|
| **Opportunity** | 策略扫描发现的机会，包含股票信息、触发日期、触发价格等 |
| **BaseOpportunityAdapter** | Adapter 基类，用户需要继承并实现 `process` 方法 |
| **AdapterDispatcher** | 适配器分发器（位于 strategy 模块），负责加载和调用 adapter |
| **HistoryLoader** | 历史模拟结果加载器，用于获取历史胜率等统计信息 |
| **AdapterValidator** | Adapter 验证器，用于验证 adapter 是否可用 |

### 业务概念串联

```
策略扫描 (Scanner)
    ↓
发现机会列表 (List[Opportunity])
    ↓
Core Adapter（批量查找模拟结果）
    ↓
准备数据：opportunity + 模拟结果（可选）
    ↓
AdapterDispatcher 分发
    ↓
加载配置的 Actions (如 ["console", "notification"])
    ↓
每个 Action 处理机会列表和模拟结果
    ↓
用户自定义处理（输出到控制台、发送通知、数据分析等）
```

**关键设计点**：
- **Core 模块**：负责批量查找模拟结果，将数据传递给 action
- **Userspace 模块**：用户自定义的 action，实现后续处理逻辑
- 支持配置是否加载模拟结果，以及传递哪些数据给 action
- 每个 action 独立配置，互不影响

---

## 文件夹结构

```
core/modules/adapter/
├── __init__.py                  # 模块导出
├── base_adapter.py              # BaseOpportunityAdapter 基类
├── adapter_validator.py         # Adapter 验证器
└── history_loader.py            # 历史模拟结果加载器

userspace/adapters/              # 用户自定义 adapter
├── console/
│   ├── adapter.py               # ConsoleAdapter 示例（输出到控制台，查找历史统计）
│   └── settings.py              # ConsoleAdapter 配置
└── example/
    ├── adapter.py               # 示例 Adapter
    └── settings.py              # 示例配置
```

---

## 快速使用

### 1. 创建自定义 Action

在 `userspace/adapters/{action_name}/action.py` 中创建：

```python
from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity
from typing import List, Dict, Any, Optional

class MyAction(BaseOpportunityAdapter):
    """自定义 Action"""
    
    def process(
        self,
        opportunities: List[Opportunity],
        simulation_results: Optional[Dict[str, Any]],  # 可选：模拟结果
        context: Dict[str, Any]
    ) -> None:
        """处理机会列表和模拟结果"""
        date = context.get('date')
        strategy_name = context.get('strategy_name')
        
        # 处理逻辑
        for opp in opportunities:
            self.log_info(f"发现机会: {opp.stock_name} @ {opp.trigger_date}")
            
            # 如果有模拟结果，可以使用
            if simulation_results:
                stock_history = simulation_results.get(opp.stock_id)
                if stock_history:
                    win_rate = stock_history.get('win_rate', 0.0)
                    # ... 使用模拟结果
            
            # ... 你的处理逻辑
```

### 2. 配置 Action（可选）

在 `userspace/adapters/{action_name}/settings.py` 中：

```python
settings = {
    'load_simulation_results': True,  # 是否加载模拟结果
    'output_format': 'json',
    # ... 其他配置
}
```

### 3. 在策略中启用 Action

在策略的 `scanner_settings.yaml` 中配置：

```yaml
action_names:
  - console
  - my_action

# 可选：配置是否加载模拟结果
load_simulation_results: true
```

**注意**：Core Adapter 会根据配置自动批量查找模拟结果，并传递给 action。如果配置了 `load_simulation_results: false`，则只传递 opportunity 对象。

---

## 核心组件

### BaseOpportunityAdapter

**职责**：
- 定义 adapter 接口（`process` 方法）
- 提供配置加载（从 `settings.py`）
- 提供日志记录方法（`log_info`, `log_warning`, `log_error`）
- 提供默认输出方法（当所有 adapter 失败时使用）

**不负责**：
- 不负责加载 adapter（由 `AdapterDispatcher` 负责）
- 不负责验证 adapter（由 `AdapterValidator` 负责）

### HistoryLoader

**职责**：
- 加载单只股票的历史模拟统计（胜率、平均收益等）
- 加载最新的会话汇总

**不负责**：
- 不负责计算统计（由 PriceFactorSimulator 负责）
- 不负责存储结果（由 ResultPathManager 负责）

### Console Action（示例）

**说明**：框架将提供一个 `console` action 示例，用于在命令行输出机会信息，并显示 Core Adapter 查找的模拟结果（如果有）。此功能尚未实现，但已规划。

**用途**：
- 作为 action 实现的参考示例
- 展示如何接收和使用模拟结果
- 演示如何在控制台格式化输出机会信息

### AdapterValidator

**职责**：
- 验证 adapter 是否存在且可用
- 检查 adapter 是否继承 `BaseOpportunityAdapter`
- 检查 adapter 是否实现 `process` 方法

**不负责**：
- 不负责加载 adapter（由 `AdapterDispatcher` 负责）
- 不负责调用 adapter（由 `AdapterDispatcher` 负责）

---

## 与 Strategy 模块的关系

- **Adapter 模块**提供基类和工具
- **Strategy 模块**的 `AdapterDispatcher` 负责加载和调用 adapter
- **Scanner** 在扫描完成后，通过 `AdapterDispatcher` 分发机会到配置的 adapter

---

## 相关文档

- **[user_guide.md](./user_guide.md)**：Userspace 使用指南（新增 adapter、settings、在策略中启用）
- **[architecture.md](./architecture.md)**：详细架构设计
- **[decisions.md](./decisions.md)**：重要决策记录

> **提示**：在 userspace 里新增或修改 adapter 时先看 [user_guide.md](./user_guide.md)；如需详细设计请参考 [architecture.md](./architecture.md)。

---

**文档结束**
