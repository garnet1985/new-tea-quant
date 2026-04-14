# 数据源用户指南（userspace）

本指南介绍如何在 `userspace/data_source/` 里：

- 选择并启用现有数据源（`mapping.py`）
- 新增/修改数据源抓取逻辑（`handlers/`）
- 配置外部数据提供方（`providers/`）

---

## 1. 先理解三件事（大白话）

### 1) data source 是什么？

就是一种“要抓的数据”，例如股票列表、K 线、财报、宏观指标。

在本项目里，它对应 `userspace/data_source/mapping.py` 的一个 key（比如 `stock_klines`）。

### 2) handler 是什么？

handler 负责把“我要抓什么”变成可执行的任务，并把结果清洗成可以入库的行数据。

- fetch：生成任务（调用哪些 API、怎么拆分批次、依赖哪些上下文）
- normalize：把原始结果变成统一结构（字段名、类型、缺失值处理）

### 3) provider 是什么？

provider 就是“具体怎么调用外部数据平台 API”的实现（例如 Tushare / AKShare / EastMoney / Sina）。

handler 会去调用 provider 提供的方法拿到原始数据。

---

## 2. 用现有数据源（只配置不写代码）

### Step 1. 配置 provider（可选）

以 Tushare 为例：

- 创建 `userspace/data_source/providers/tushare/auth_token.txt`（一行 token）
- 或设置环境变量 `TUSHARE_TOKEN`

详见 [providers/README.md](providers/README.md)。

### Step 2. 启用/禁用 data source

编辑 `userspace/data_source/mapping.py`，每个 data source 形如：

```python
DATA_SOURCES = {
  "stock_klines": {
    "handler": "stock_klines.KlineHandler",
    "is_enabled": True,
    "depends_on": ["stock_list", "latest_trading_date"],
  },
}
```

- `handler`：指向 `handlers/<模块>/handler.py` 里的类（框架按约定加载）
- `depends_on`：
  - 其它 data source（如 `stock_list`）
  - 保留关键字（如 `latest_trading_date`，由框架直接注入）

### Step 3. 运行更新

在仓库根目录执行 renew：

```bash
python start-cli.py -r
```

---

## 3. 新增一个 data source（推荐流程）

### Step 1. 取一个新的 data source 名称

例如：`my_custom_data`。  
它会成为 `mapping.py` 的一个 key，也会对应一个 handler 模块目录名。

### Step 2. 新建 handler 目录与文件

创建：

```text
userspace/data_source/handlers/my_custom_data/
├── handler.py
└── config.py   # 可选：放 handler 参数与默认值
```

### Step 3. 实现 handler 类

参考 `handlers/*/handler.py` 的现有实现。一般你需要：

- 声明 `data_source` / `description`
- 实现 `fetch(...)`（生成 tasks / jobs）
- 实现 `normalize(...)`（输出标准化 rows）

（具体抽象基类与任务模型见 core 的 `modules.data_source` 文档与代码）

### Step 4. 在 `mapping.py` 注册并启用

```python
DATA_SOURCES["my_custom_data"] = {
  "handler": "my_custom_data.MyCustomDataHandler",
  "is_enabled": True,
  "depends_on": ["latest_trading_date"],
}
```

### Step 5. 先小范围验证，再放开

建议顺序：

- 先只跑一次，确认能写库、字段正确
- 再逐步增加股票/日期范围，观察耗时与失败重试情况

---

## 4. 常见问题

### Q1: handler 找不到/加载失败？

- 检查 `mapping.py` 的 `handler` 字段是否符合约定：`<模块>.<类名>`
- 检查文件是否存在：`handlers/<模块>/handler.py`

### Q2: `depends_on` 写了但 context 里没有？

- 依赖别的 data source：确保它也启用，并且执行顺序能满足
- 依赖保留关键字：确保 key 拼写正确（保留关键字由框架解析注入）

### Q3: provider 配置不生效？

- 先检查 `providers/<name>/README.md` 的配置约定
- 再检查是否被环境变量覆盖

---

## 5. 参考

- userspace 入口：[README.md](README.md)
- providers 说明：[providers/README.md](providers/README.md)
- Core 模块文档：`core/modules/data_source/README.md`
- 入口文档：[README.md](README.md)

