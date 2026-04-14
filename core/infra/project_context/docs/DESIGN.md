# Project Context 详细设计

**版本：** `0.2.0`

本文档描述实现向行为；总览见 [架构文档](./ARCHITECTURE.md)。

**相关文档**：[架构总览](./ARCHITECTURE.md) · [API](./API.md) · [决策记录](./DECISIONS.md)

---

## 1. 项目根检测（`PathManager.get_root`）

1. 若 `_root_cache` 已设，直接返回。
2. 从 `path_manager.py` 所在路径向上遍历父目录。
3. 若目录下存在任一根标记且存在：`.git`、`pyproject.toml`、`setup.py`、`requirements.txt`、`start.py`，则缓存并返回该目录。
4. 否则使用固定层级的 `parent^5` 作为 fallback 并缓存。

---

## 2. `core()` 与 `userspace()`

- **`core()`**：优先 `项目根/core`；若不存在则尝试 `项目根/app/core`；仍不存在则返回 `项目根/core`（不创建）。
- **`userspace()`**：依次检查 `NEW_TEA_QUANT_USERSPACE_ROOT`、`NTQ_USERSPACE_ROOT`；若存在且为有效路径则返回；否则 `项目根/userspace`（不存在亦返回该 Path）。

---

## 3. `ConfigManager` 合并

- **`load_with_defaults`**：先加载默认文件；用户路径存在则加载并 `_deep_merge_config`（`deep_merge_fields` 对同名 dict 做一层深度合并；`override_fields` 参与浅层合并语义）。
- **`load_core_config`**：`default_config/{name}.json` + `userspace/config/{name}.json`，`file_type` 固定 JSON。
- **`load_database_config`**：合并 `database/common`、按类型加载 `database/{type}`、展开 `_advanced`、合并用户侧扁平或 wrapper 格式，最后 **`load_with_env_vars`**（`DB_{TYPE}_*`）。

---

## 4. Python 配置加载

- `importlib.util.spec_from_file_location` 生成唯一模块名，执行模块后读取约定变量名（默认 `settings`），必须为 `dict`。

---

## 5. `ProjectContextManager.core_info`

1. 读 `PathManager.core() / "core_meta.json"`，成功则 `json.loads`。
2. 失败则 `from core.system import system_meta` 并 `to_dict()`。
3. 仍失败返回 `None`。

---

## 6. `get_module_config` 与 Worker

- 运行时 `from core.infra.worker.multi_process.task_type import TaskType`，将 Worker 配置中的字符串映射为枚举；避免在 `project_context` 顶层 import `worker`，减轻与 `worker -> ConfigManager` 的静态环。
