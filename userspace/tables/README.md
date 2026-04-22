# 用户表（`userspace/tables/`）

在这里按约定新增**自己的数据库表**：每个表一个小目录，写好 `schema.py` + `model.py`，启动 **`DataManager`** 时会自动发现并注册，`get_table`、导出/备份、在 loader 里按表名读取等能力与内置表一致。

---

## 一分钟上手

1. 在 `userspace/tables/` 下新建文件夹（名称随意，建议能看出用途，例如 `my_signals`）。
2. 目录里放 **`schema.py`**（表结构）和 **`model.py`**（必须是 `DbBaseModel` 子类）。
3. 重启进程或重新初始化 **`DataManager`**。
4. 用 `dm.get_table("你在 schema 里写的表名")` 检查是否能取到实例。

---

## 从 0 建一张表

### Step 1）目录

例如先做成这样即可：

```text
userspace/tables/my_signals/
├── schema.py
└── model.py
```

### Step 2）编写 `schema.py`

文件内需有全局变量 **`schema`**（`dict`），至少包含 **`name`**、**`primaryKey`**、**`fields`**。字段怎么写最简单：**复制** `core/tables` 里结构相近的一张表里的 `schema.py`，改 `name` 和字段列表。

示例（主键字符串 + 一段文本）：

```python
# userspace/tables/my_signals/schema.py
schema = {
    "name": "cust_my_signals",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "主键",
        },
        {
            "name": "note",
            "type": "text",
            "isRequired": True,
            "nullable": True,
            "description": "备注",
        },
    ],
}
```

建议表名使用 **`cust_`** 等与内置 **`sys_`** 区分的前缀，避免和自带表重名。

### Step 3）编写 `model.py`

- 继承 **`DbBaseModel`**。
- **`load_schema`**：在类里**覆盖** `load_schema()`，直接 `return` 同目录 `schema`（下面示例）。这样在 userspace 下不依赖其它目录是否扫描你的文件。
- **`__init__`**：用同一套 `schema["name"]` 调用 `super().__init__(...)`。

```python
# userspace/tables/my_signals/model.py
from core.infra.db import DbBaseModel
from .schema import schema as _schema


class MySignalsModel(DbBaseModel):
    def load_schema(self):
        return _schema

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    # 按需增加 load_one / upsert_many 等方法
```

### Step 4）自检

```python
from core.modules.data_manager import DataManager

dm = DataManager(is_verbose=True)
m = dm.get_table("cust_my_signals")
assert m is not None
```

### Step 5）（按需）建物理表

若数据库里还没有这张表：在 **`model` 已能拿到且 `load_schema` 正常**的前提下，可对实例调用 **`create_table()`**（定义见 `DbBaseModel`）；是否在你项目里统一批量建表，按现有流程即可。

---

## 目录结构（示意）

```text
userspace/tables/
├── README.md
├── my_signals/
│   ├── schema.py
│   └── model.py
└── another_table/
    ├── schema.py
    └── model.py
```

允许子目录嵌套：只要在某个目录下放了一份 **`schema.py`**，该目录会被当成一张表的根目录参与发现。

---

## 更多说明

- 发现规则与注册细节：`core/modules/data_manager/docs/DESIGN.md`
- 字段类型、索引等写法：对照 `core/tables/**/schema.py` 与 `SchemaManager` 校验规则
