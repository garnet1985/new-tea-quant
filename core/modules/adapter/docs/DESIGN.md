# Adapter 设计说明

**版本：** `0.2.0`

userspace 扩展布局、动态加载、`process` 上下文，以及与 `AdapterDispatcher` 的协作。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## userspace 目录约定

```text
userspace/extensions/adapters/
├── console/
│   ├── adapter.py      # 必须：继承 BaseOpportunityAdapter 的类
│   └── settings.py     # 可选：顶层 settings 或 config（dict）
└── <adapter_name>/
    ├── adapter.py
    └── settings.py
```

- **模块路径**：`userspace.extensions.adapters.<adapter_name>.adapter`
- **类查找**：取模块中**第一个**「继承 `BaseOpportunityAdapter` 且非基类」的类（`AdapterLoader` / 校验器 / 分发器同一规则）
- **配置**：导入 `userspace.extensions.adapters.<name>.settings`，读取 `settings` 或 `config`；缺失则为 `{}`

---

## 策略配置

scanner 段使用 `adapters`（字符串或列表）。校验经 `Adapter.validate(name)`；失败提示检查 `userspace/extensions/adapters/<name>/adapter.py`。

---

## `process` 与上下文

```text
process(opportunities: List[Opportunity], context: Dict[str, Any]) -> None
```

常见 `context` 键：

- `date` / `strategy_name` / `scan_summary` / `date_meta`
- `price_history`：`{ "session_summary": dict|None, "by_stock": {stock_id: stats} }`（由 strategy 推送）

---

## 运行时行为（AdapterDispatcher）

1. 组装 / 保留 `context["price_history"]`
2. `adapter_names` 为空 → `BaseOpportunityAdapter.default_output`
3. 非空 → 按名 `Adapter.load_class`，实例化后 `process`
4. 全部失败 → `default_output`

---

## 设计决策

### 1. userspace 包路径与目录名一致

约定 `userspace/extensions/adapters/<name>/`，配置只写 `<name>`，与其它 extensions 一致。

### 2. 模块内第一个合法子类即实现

鼓励每个 `adapter.py` 只放一个主类；多子类时依赖枚举顺序。

### 3. 额外信息由 strategy 推送

adapter 只消费标准机会列表 + context；不 import strategy、不读模拟产物目录。

### 4. 分发与兜底放在 strategy.Scanner

`AdapterDispatcher` 在 strategy；加载规则下沉到 `AdapterLoader` 避免与校验器重复。
