# Data Source 设计说明

**模块：** `modules.data_source` · **版本：** `0.4.0`

API 以根目录 [API.md](../API.md) 为准。实现以 `core/data_source_manager.py`、`core/service/manager_helper.py` 为准。

---

## 1. userspace 布局

| 路径 | 作用 |
| --- | --- |
| `userspace/data_source/mapping.py` | **`DATA_SOURCES`** |
| `userspace/extensions/data_source/handlers/<name>/settings.py` | 各源 **`settings`**（顶层 **`table`**） |
| `userspace/data_source/handlers/.../handler.py` | Handler 实现 |
| `userspace/data_source/providers/` | Provider 包 |

---

## 2. Schema 与表绑定

- **`CONFIG.table`** → **`DataManager.get_table`** → **`load_schema()`**
- Handler 输出与 schema 对齐；不维护独立 schema 文件

---

## 3. Config / Provider 发现

1. handler config：约定路径或 `handlers/` 树内按 key 查找
2. Provider：扫描 `userspace.data_source.providers` 下 `BaseProvider` 子类

---

## 4. 执行与 `is_dry_run`

- **`is_dry_run`** 为真时跳过写库，仍可抓取与标准化

---

## 5. 设计决策

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [BUFFER_PIPELINE.md](./BUFFER_PIPELINE.md)
- [API.md](../API.md)
