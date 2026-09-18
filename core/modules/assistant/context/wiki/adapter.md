---
title: Adapter 机会适配
aliases:
  - adapter
  - opportunity
  - scanner
  - extension
summary: NTQ的扫描机会处理接口-机会适配器。
---

# 适配器：机会适配

## 什么是 Adapter

Adapter 是 Scanner（枚举引擎）的**后处理扩展点**。策略的扫描阶段结束后，框架将机会列表和上下文交给用户自定义的适配器做进一步处理。

典型用途：

- 生成自定义报告（按行业分组、按信号强度排序）

- 写入外部系统（飞书、钉钉通知）

- 做机会的二次筛选或排序

> 注意：Adapter 不是券商/数据源适配器。它不处理行情接入或下单通道，只在扫描结果产出后做后处理。

## 架构

```
core/modules/adapter/
├── adapter.py              门面：validate() / load_class()
├── contracts.py             导出 BaseOpportunityAdapter
├── core/
│   ├── base_adapter.py      BaseOpportunityAdapter (ABC)
│   ├── adapter_validator.py AdapterValidator
│   └── loader.py            AdapterLoader
└── docs/
```

| 类                        | 职责                                          |
| ------------------------ | ------------------------------------------- |
| `Adapter`                | 门面，提供 `validate(name)` 和 `load_class(name)` |
| `BaseOpportunityAdapter` | 抽象基类，用户继承它实现 `process()`                    |
| `AdapterLoader`          | 动态导入 userspace 适配器模块                        |
| `AdapterValidator`       | 验证适配器模块是否可加载                                |
| `AdapterDispatcher`      | 在 Scanner 中运行适配器，注入 `price_history`，失败回退    |

## 用户侧开发

在 `userspace/extensions/adapters/<name>/` 下创建两个文件：

### adapter.py

```python
from core.modules.adapter.contracts import BaseOpportunityAdapter

class IndustryReportAdapter(BaseOpportunityAdapter):
    def process(self, opportunities, context):
        # context 包含 price_history 等统计信息
        price_history = context.get("price_history", {})

        # 按 industry 分组
        by_industry = {}
        for opp in opportunities:
            industry = opp.get("industry", "unknown")
            by_industry.setdefault(industry, []).append(opp)

        # 输出自定义报告
        for industry, opps in by_industry.items():
            print(f"[{industry}] {len(opps)} 个机会")
            for opp in opps:
                print(f"  - {opp['entity_id']}: {opp.get('signal', '')}")

        # 返回结果（可选，框架不强制使用返回值）
        return {"total": len(opportunities), "by_industry": len(by_industry)}
```

### settings.py（可选）

```python
settings = {
    "output_format": "console",
    "group_by": "industry",
    "max_per_group": 10,
}

# 或使用 config 变量名
config = settings
```

基类自动加载 `settings.py`，可通过 `self.config` 访问。

## 配置使用

在策略 `settings.py` 中指定适配器：

```python
settings = {
    "scanner": {
        "adapter_names": "industry_report",
        # 或多个适配器：
        # "adapter_names": ["industry_report", "notification"],
    },
    ...
}
```

## 执行流程

```
Scanner 执行完毕，产出 opportunities 列表
    ↓
AdapterDispatcher 被调用
    ↓
注入 context["price_history"]（扫描期间的统计数据）
    ↓
检查 settings.scanner.adapter_names
    ├── 无适配器 → 打印 BaseOpportunityAdapter.default_output()
    └── 有适配器 → 逐个加载并调用 process(opportunities, enriched_context)
                    ├── 成功 → 使用适配器输出
                    └── 全部失败 → 回退到 default_output()
```

### AdapterDispatcher

位于 `core/modules/strategy/core/engines/scanner/helpers/adapter_dispatcher.py`，是 Scanner 引擎的一部分。它：

1. 用 `Adapter.load_class(name)` 动态加载适配器
2. 用扫描期间的统计数据丰富 context
3. 调用每个适配器的 `process(opportunities, context)`
4. 所有适配器失败时回退到 `default_output()`

## 验证

配置校验阶段调用 `Adapter.validate(name)` 检查：

- 模块文件是否存在

- 是否包含 `BaseOpportunityAdapter` 子类

- 是否实现了 `process` 方法

- 是否可实例化

```python
from core.modules.adapter import Adapter

Adapter.validate("industry_report")  # True/False
cls = Adapter.load_class("industry_report")  # 返回类对象
```

## BaseOpportunityAdapter

```python
class BaseOpportunityAdapter(ABC):
    def __init__(self):
        self.config = {}  # 自动加载 settings.py
        self.logger = ...  # 内置日志器

    @abstractmethod
    def process(self, opportunities, context):
        """处理机会列表，返回自定义结果"""
        raise NotImplementedError

    def default_output(self):
        """默认输出，所有适配器失败时使用"""
        return "扫描完成，未配置有效适配器"
```

## 设计约束

| 规则                   | 说明                            |
| -------------------- | ----------------------------- |
| 适配器读 context，不导入策略模块 | 保持解耦                          |
| 适配器输出是静态结果           | 控制台报告或外部集成，不影响回测结果            |
| 多适配器串联执行             | 按配置顺序依次调用                     |
| 失败自动回退               | 所有适配器失败时使用 `default_output()` |

## 与其他模块的关系

| 模块                     | 关系                                         |
| ---------------------- | ------------------------------------------ |
| **strategy (scanner)** | AdapterDispatcher 在扫描引擎内部调用适配器             |
| **data\_contract**     | 适配器可通过 context 获取 price\_history 统计        |
| **userspace**          | 适配器代码放在 `userspace/extensions/adapters/` 下 |

