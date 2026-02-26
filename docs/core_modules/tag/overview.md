# Tag 模块概览

> **提示**：本文档提供 Tag 模块的快速上手视图。  
> 详细的设计理念、架构设计和决策记录请参考同目录下的 `architecture.md` 和 `decisions.md`。

## 📋 模块简介

`Tag` 模块是系统的**标签预计算框架**，用于按业务场景批量计算并存储实体（股票等）的属性/状态。模块的最核心价值在于：**一次计算，多次复用，可追溯，可跨策略**。

**为什么不是“每次现算就好”？**

- **一次计算，多次复用**：标签被写入数据库后，可以被任意数量的策略、分析脚本、报表工具直接复用，而不需要在每个回测 / 每个脚本里重复实现和执行同样的计算逻辑。
- **可追溯**：所有标签值带有 `as_of_date`、`tag_definition_id` 和 `scenario` 信息，可以在事后精确还原「某天、某只股票、某个标签在当时的取值」，方便 Debug 和审计。
- **跨策略共享**：市值分类、动量因子、风险分层等标签可以由 Tag 系统一次性计算，然后同时服务多个策略和分析任务，避免每个策略都维护一套自己的指标/标签实现。

**核心特性**：

- **预计算 + 持久化**：把昂贵、通用的计算前移到 Tag 系统，结果存入数据库（`tag_scenario` / `tag_definition` / `tag_value`），后续所有回测和线上逻辑都只做「读」而不是「算」
- **配置驱动**：通过 `settings.py` 声明业务场景（Scenario）和标签列表（Tags），无需改框架代码
- **增量更新**：支持 `incremental` / `refresh` 两种更新模式，避免重复全量计算
- **多进程并行**：按实体（如股票）分割 jobs，使用 Worker 模块并行计算
- **结构化标签值**：使用 JSON 存储标签值，支持复杂结构（键值对、数组等）

**与其他模块的关系**：

- 与 `DataManager`：标签数据通过 DataManager 的 `stock.tags` 服务读写
- 与 `Strategy`：策略可以直接使用已计算好的标签（如动量因子、市值分类）
- 与 `Worker`：TagManager 使用多进程 Worker 执行实体级别的标签计算

---

## 📁 模块的文件夹结构

```text
core/modules/tag/
├── core/
│   ├── base_tag_worker.py                  # TagWorker 基类
│   ├── tag_manager.py                      # TagManager，场景发现与调度
│   ├── enums.py                            # 更新模式、文件名等枚举
│   ├── config.py                           # Tag 系统全局配置（如 scenarios 根目录）
│   ├── models/
│   │   ├── scenario_model.py               # Scenario 元数据模型
│   │   └── tag_model.py                    # TagDefinition 模型
│   └── components/
│       ├── helper/
│       │   ├── job_helper.py               # Job 构建与性能决策
│       │   └── tag_helper.py               # Settings / Worker 加载工具
│       └── tag_worker_helper/
│           └── tag_worker_data_manager.py  # 子进程数据加载与过滤
├── ARCHITECTURE.md                         # 架构文档（源材料）
└── README.md                               # 使用指南
```

用户代码所在位置：

```text
userspace/tags/
├── my_scenario/
│   ├── settings.py                         # 场景与标签配置
│   └── tag_worker.py                       # 业务计算逻辑（继承 BaseTagWorker）
└── ...
```

---

## 🚀 模块的使用方法（概览）

### 1. 定义业务场景与标签

```python
# userspace/tags/my_scenario/settings.py
Settings = {
    "name": "my_scenario",
    "display_name": "我的业务场景",
    "description": "这是一个示例场景",
    "is_enabled": True,
    "target_entity": {"type": "stock_kline_daily"},
    "update_mode": "incremental",
    "incremental_required_records_before_as_of_date": 60,
    "tags": [
        {
            "name": "my_tag",
            "display_name": "我的标签",
            "description": "这是一个示例标签",
        }
    ],
}
```

### 2. 实现 TagWorker

```python
# userspace/tags/my_scenario/tag_worker.py
from core.modules.tag.core.base_tag_worker import BaseTagWorker
from core.modules.tag.core.models.tag_model import TagModel
from typing import Dict, Any, Optional

class MyTagWorker(BaseTagWorker):
    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel,
    ) -> Optional[Dict[str, Any]]:
        daily_klines = historical_data["klines"]["daily"]
        # ... 计算逻辑 ...
        return {"value": {"my_value": 123.45}}
```

### 3. 执行标签计算

```python
from core.modules.tag.core.tag_manager import TagManager

tag_manager = TagManager(is_verbose=True)

# 执行所有启用的场景
tag_manager.execute()

# 或仅执行单个场景
tag_manager.execute(scenario_name="my_scenario")
```

---

## 📊 标签数据访问（通过 DataManager）

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager()
tag_service = data_mgr.stock.tags

# 查询某个实体在某日的所有标签
tag_values = tag_service.load_tag_values(
    entity_id="000001.SZ",
    as_of_date="20251219",
)
```

---

## 📚 模块详细文档

- **[user_guide.md](./user_guide.md)**：Userspace 使用指南（新增场景、settings、tag_worker、执行与读取）
- **[architecture.md](./architecture.md)**：架构文档，包含数据模型、组件职责、多进程执行和数据流设计
- **[decisions.md](./decisions.md)**：重要决策记录，说明表结构、多进程策略、Chunk 模式等设计取舍

> **阅读建议**：在 userspace 里新增标签场景时先看 [user_guide.md](./user_guide.md)；再阅读本文档与 `architecture.md` 理解内部设计，最后阅读 `decisions.md` 了解设计背景与权衡。 
