---
title: write adapter 写一个机会适配器
aliases:
  - adapter
  - scanner
  - extension
  - post-processing
  - 适配器
  - 扫描后处理
summary: 给扫描结果写后处理适配器，并在策略 settings 里用 scanner.adapters 挂上。
---

# 如何编写适配器

## 什么是适配器

适配器是扫描结束后的后处理扩展点。框架把机会列表和上下文交给你写的适配器。

典型用途：

- 生成自定义报告（按行业分组、按信号强度排序）

- 写入外部系统（通知、飞书）

- 机会的二次筛选或排序

## 创建文件

在 `userspace/extensions/adapters/<name>/` 下创建：

```
userspace/extensions/adapters/my_report/
├── adapter.py       适配器实现
└── settings.py      可选配置
```

## adapter.py

```python
from core.modules.adapter.contracts import BaseOpportunityAdapter

class IndustryReportAdapter(BaseOpportunityAdapter):
    def process(self, opportunities, context):
        # context 包含 price_history 等统计信息
        price_history = context.get("price_history", {})

        # 按行业分组
        by_industry = {}
        for opp in opportunities:
            industry = opp.get("industry", "unknown")
            by_industry.setdefault(industry, []).append(opp)

        # 输出自定义报告
        for industry, opps in sorted(by_industry.items()):
            print(f"[{industry}] {len(opps)} 个机会")
            for opp in opps:
                print(f"  - {opp['entity_id']}: {opp.get('signal', '')}")

        return {"total": len(opportunities), "by_industry": len(by_industry)}
```

### process 方法

| 参数              | 说明                                  |
| --------------- | ----------------------------------- |
| `opportunities` | 机会列表，每个元素含 `entity_id`、`signal` 等字段 |
| `context`       | 上下文字典，含 `price_history` 等扫描统计       |

返回值可选——框架不强制使用返回值。

## settings.py（可选）

```python
settings = {
    "output_format": "console",
    "group_by": "industry",
    "max_per_group": 10,
}
```

基类自动加载 `settings.py`，通过 `self.config` 访问。

## 在策略中配置

策略 `settings.py` 中指定适配器：

```python
"scanner": {
    "adapters": "my_report",
    # 多个适配器串联：
    # "adapters": ["my_report", "notification"],
}
```

## 执行流程

```
Scanner 执行完毕，产出 opportunities 列表
    ↓
框架注入 context["price_history"]
    ↓
检查 settings.scanner.adapters
    ├── 无适配器 → 打印默认摘要
    └── 有适配器 → 逐个加载并调用 process()
                    ├── 成功 → 使用适配器输出
                    └── 全部失败 → 回退到默认摘要
```

## 验证适配器

```python
from core.modules.adapter import Adapter

Adapter.validate("my_report")     # 返回 (是否通过, 说明文字)
cls = Adapter.load_class("my_report")  # 返回类对象
```

配置校验阶段会自动调用 `validate()` 检查适配器是否可加载。

## 设计约束

| 规则                   | 说明                            |
| -------------------- | ----------------------------- |
| 适配器读 context，不导入策略模块 | 保持解耦                          |
| 适配器输出是静态结果           | 控制台报告或外部集成，不影响回测结果            |
| 多适配器串联执行             | 按配置顺序依次调用                     |
| 失败自动回退               | 所有适配器失败时使用默认摘要 |

## 多适配器串联

```python
"scanner": {
    "adapters": ["industry_report", "notification"],
}
```

框架按顺序依次调用每个适配器的 `process()`，每个适配器独立处理同一份机会列表。
