# Adapter 用户指南（userspace）

本指南面向“要把扫描结果接到自己渠道”的用户，比如：

- 控制台打印
- 发 webhook
- 写到文件
- 推到消息系统

Adapter 不负责选股逻辑，只负责消费 Strategy 产出的机会结果。

---

## 1. 运行链路（先理解）

1. Strategy 扫描得到 `Opportunity` 列表
2. Scanner 读取策略配置里的 `scanner.adapters`
3. 框架按顺序加载 `userspace/adapters/<name>/adapter.py`
4. 调用每个 adapter 的 `process(opportunities, context)`

所以你只要专注 `process(...)`，不用关心扫描调度细节。

---

## 2. 目录约定

每个 adapter 一个目录：

```text
userspace/adapters/<adapter_name>/
├── adapter.py
└── settings.py
```

- `<adapter_name>` 必须和策略里 `scanner.adapters` 的字符串一致
- `adapter.py` 必须有一个继承 `BaseOpportunityAdapter` 的类
- `settings.py` 建议提供模块级 `settings` 字典

---

## 3. 最小模板

### `settings.py`

```python
settings = {
    "name": "my_adapter",
    "format": "simple",
    "enabled": True,
}
```

### `adapter.py`

```python
from typing import Any, Dict, List
from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity


class MyAdapter(BaseOpportunityAdapter):
    def process(self, opportunities: List[Opportunity], context: Dict[str, Any]) -> None:
        if not self.get_config("enabled", True):
            return
        strategy_name = context.get("strategy_name", "unknown")
        self.log_info(f"strategy={strategy_name}, count={len(opportunities)}")
        for opp in opportunities:
            print(f"{opp.stock_id},{opp.stock_name},{opp.trigger_date},{opp.trigger_price}")
```

---

## 4. 在策略中启用

在策略 `settings.py` 的 `scanner` 段加入：

```python
"scanner": {
    "max_workers": "auto",
    "adapters": ["console", "my_adapter"],
}
```

说明：

- 可以配置多个 adapter，按列表顺序调用
- 列表为空时，系统会走默认输出逻辑

---

## 5. 运行命令

```bash
python start-cli.py scan --strategy example
```

如果只想确认 adapter 能加载，先用一个很小的策略样本跑一轮 scan。

---

## 6. `context` 里常用信息

不同流程可能略有差异，常见字段包括：

- `date`：扫描日期
- `strategy_name`：策略名
- `scan_summary`：扫描汇总信息

建议写法：`context.get("xxx")`，避免强依赖某个字段必定存在。

---

## 7. 常见问题

### Q1：提示 adapter 不可用？

先检查：

- `userspace/adapters/<name>/adapter.py` 是否存在
- 类是否继承 `BaseOpportunityAdapter`
- 策略里的 `scanner.adapters` 名字是否和目录名一致

### Q2：`settings.py` 不生效？

`BaseOpportunityAdapter` 会读取模块级 `settings`（或 `config`）字典。  
请确认变量名和层级正确。

### Q3：一个 adapter 报错会中断全部吗？

单个 adapter 失败通常会记录日志，然后继续执行后面的 adapter。  
建议在 `process` 内部也做好异常保护，避免影响后续链路。

---

## 8. 实战建议

- 先用 `example/` 改出你的第一版，再抽成新目录
- `process` 内尽量只做“展示/分发”，不要塞策略计算逻辑
- 对外部 IO（HTTP、文件）加超时和错误日志
- 结果格式先稳定，再扩字段，避免下游反复改解析

---

## 9. 参考

- 入口文档：`userspace/adapters/README.md`
- 模块设计：`core/modules/adapter/README.md`
- 示例：`userspace/adapters/console`、`userspace/adapters/example`
