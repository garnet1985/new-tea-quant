# Adapter 设计说明

**版本：** `0.2.0`

本文档说明 **userspace 扩展布局**、**动态加载规则**、**`process` 上下文**，以及与 **`AdapterDispatcher`** 的协作关系。实现以 `base_adapter.py`、`adapter_validator.py`、`core/modules/strategy/components/scanner/adapter_dispatcher.py` 为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## userspace 目录约定

每个 adapter 占一个与名称一致的子目录：

```text
userspace/adapters/
├── console/
│   ├── adapter.py      # 必须：实现继承 BaseOpportunityAdapter 的类
│   └── settings.py     # 可选：顶层变量 settings 或 config（dict）
└── <adapter_name>/
    ├── adapter.py
    └── settings.py
```

- **模块路径**：`userspace.adapters.<adapter_name>.adapter`（与目录名一致）。
- **类查找**：加载模块后取 **第一个** 满足「继承 `BaseOpportunityAdapter` 且非基类本身」的类；验证器与分发器使用相同规则。
- **配置**：`BaseOpportunityAdapter._load_config` 导入 `userspace.adapters.<adapter_name>.settings`，读取模块级 **`settings`** 或 **`config`**；缺失则为 `{}`。

---

## 策略配置

在策略的 **scanner** 段使用 **`adapters`**：

- 类型：字符串（单个名）或字符串列表；空或缺省时等价于仅依赖分发器侧的「无配置」分支（使用 `default_output`）。
- 默认占位：解析逻辑会将缺省补为 `["console"]`（见 `ScannerSettings`），具体以策略设置代码为准。

校验：`ScannerSettings._validate_adapters` 对列表中每个名称调用 **`validate_adapter(name)`**，失败则写入校验报告并提示检查 `userspace/adapters/<name>/adapter.py`。

---

## `process` 与上下文

```text
process(opportunities: List[Opportunity], context: Dict[str, Any]) -> None
```

**`context`** 由 Scanner 管线传入，常见键包括：

| 键 | 说明 |
| --- | --- |
| `date` | 扫描日期 |
| `strategy_name` | 策略名 |
| `scan_summary` | 扫描汇总（如股票数等，依实现而定） |

`Opportunity` 为策略模块定义的数据类；adapter 不应修改框架扫描语义，仅消费数据。

---

## 运行时行为（AdapterDispatcher）

1. **`adapter_names` 为空**：直接调用 **`BaseOpportunityAdapter.default_output`**，不再加载 userspace。
2. **非空**：按顺序对每个名称 `importlib.import_module("userspace.adapters.{name}.adapter")`，取第一个合法子类，**无参实例化**后调用 **`process`**。
3. **任一成功**即增加成功计数；若**全部**加载失败或 `process` 抛错导致成功数为 0，则 **`default_output`**。
4. 单个 adapter 失败会记录错误日志并继续尝试下一个。

---

## HistoryLoader 与结果目录

`HistoryLoader` 通过 **`VersionManager.resolve_price_factor_version(..., version_spec="latest")`** 定位模拟版本目录，再用 **`ResultPathManager`** 解析单股 JSON 与会话汇总文件。无文件或解析失败时返回 **`None`**，调用方需容错。

统计字段含义见 `HistoryLoader.load_stock_history` 文档字符串；ROI / `result` / `duration_in_days` 等来自价格模拟落盘格式。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)
