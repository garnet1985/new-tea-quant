# Project Context 详细设计

**版本：** `0.4.0`

本文档描述实现向行为；总览见 [架构文档](./ARCHITECTURE.md)。

**相关文档**：[架构总览](./ARCHITECTURE.md) · [决策记录](./DECISIONS.md) · [API契约](../api.yaml)

---

## 1. Facade + Abstract Interface 设计

### **架构核心**

- **ProjectContextAPI (抽象类)：** 定义所有对外API（16个核心API），确保契约稳定。
- **ProjectContextManager (实现类)：** 实现所有API，组合内部Manager提供功能，对外唯一入口。
- **内部Manager（私有）：** `PathManager`、`ConfigManager`、`FileManager`、`DiscoveryManager` 变成内部实现，不对外暴露。

### **设计原则**

- **单一入口点：** 用户只通过 `ProjectContextManager` 访问功能。
- **API契约明确：** 抽象类定义所有API，契约稳定。
- **防止误用：** 内部Manager不暴露，防止用户错误调用。
- **实例方法：** 所有API都是实例方法（符合Python惯例，易于测试）。

---

## 2. 路径API设计（5个）

### **命名规范统一**

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 根目录 | `get_xxx_root()` | `get_project_root()`, `get_core_root()`, `get_userspace_root()` |
| 目录 | `get_xxx_directory()` | `get_strategy_directory()`, `get_tag_directory()` |
| 文件路径 | `get_xxx_path()` | （暂未对外暴露） |

### **核心路径发现**

- **项目根目录（`get_project_root`）：**
  1. 从 `project_context_manager.py` 所在路径向上遍历父目录。
  2. 若目录下存在任一根标记（`.git`、`pyproject.toml`、`setup.py`、`requirements.txt`、`start.py`），则缓存并返回该目录。
  3. 否则使用固定层级的 `parent^5` 作为 fallback 并缓存。

- **core目录（`get_core_root`）：**
  - 返回 `项目根/core`。

- **userspace目录（`get_userspace_root`）：**
  - 依次检查环境变量 `NEW_TEA_QUANT_USERSPACE_ROOT`、`NTQ_USERSPACE_ROOT`。
  - 若存在且为有效路径则返回；否则返回 `项目根/userspace`。

### **缓存管理**

- **`clear_userspace_cache`：** 清理 `userspace` 路径缓存，下次调用会重新计算。
- **命名规范：** 使用 `clear_xxx_cache()` 表示清理缓存（而非 `invalidate_xxx_cache`）。

---

## 3. 配置API设计（3个）

### **配置加载**

- **`load_core_config(config_name)`：**
  - 使用 `DiscoveryManager.load_overridable_config("", config_name)`。
  - 配置不存在时返回空字典（不抛出异常）。

- **`load_database_config(database_type)`：**
  - 合并 `database/common`、按类型加载 `database/{type}`。
  - 展开 `_advanced`、合并用户侧扁平或 wrapper 格式。
  - 最后应用环境变量覆盖（`DB_{TYPE}_*`）。

- **`load_data_config()`：**
  - 加载 `data.json` 配置。

### **配置发现**

- **`discover_configs()`：**
  - 使用 `DiscoveryManager.discover_configs(domain="")` 发现所有配置名称。
  - 对每个配置调用 `load_overridable_config` 加载内容。
  - 返回配置名称到配置字典的映射。

---

## 4. 发现API设计（3个）

### **策略发现**

- **`discover_strategies()`：**
  - 扫描 `userspace/strategies/` 目录。
  - 返回所有子目录名称（排除隐藏目录）。
  - 按字母顺序排序返回。

### **Tag发现**

- **`discover_tags()`：**
  - 扫描 `userspace/extensions/tags/` 目录。
  - 返回所有子目录名称（排除隐藏目录）。
  - 按字母顺序排序返回。

---

## 5. 文件API设计（2个）

### **文件查找**

- **`find_file(filename, search_dir, recursive)`：**
  - 在指定目录查找单个文件。
  - 支持递归搜索（`recursive=True`）或非递归搜索（`recursive=False`）。
  - 未找到返回 `None`。

### **文件加载**

- **`load_file_content(path, encoding)`：**
  - 加载文件内容（使用指定编码）。
  - 文件不存在或加载失败返回 `None`。

---

## 6. 元数据API设计（2个）

### **版本信息**

- **`core_version()`：**
  - 获取 core 版本号（从 `core_meta.json` 或 `core.system.system_meta`）。
  - 返回版本号字符串或 `None`。

- **`core_info()`：**
  - 获取 core meta 信息（从 `core_meta.json` 或 `core.system.system_meta`）。
  - 返回 meta 信息字典或 `None`。

---

## 7. 配置发现与合并（内部实现）

### **DiscoveryManager**

- **`discover_configs(domain, pattern)`：** 扫描 core / userspace 下指定 domain 的 JSON 配置。
- **`discover_config(domain, config_id)`：** 解析配置在 core / userspace 下的路径。
- **`load_overridable_config(domain, config_id, merge_fn)`：** 加载可覆盖配置。

### **ConfigManager**

- **`load_with_defaults(default_path, user_path, deep_merge_fields, override_fields)`：** 合并默认配置与用户配置。
- **`load_json_file(path)`：** 加载JSON配置文件。
- **`parse_python_config(path, var_name)`：** 解析Python配置文件（涉及动态导入）。
- **`deep_merge_config(base, override)`：** 深度合并配置。

---

## 8. 温和失败（缺文件不抛）

- **设计原则：** 可选文件未创建时不应阻断探索性流程。
- **实现：**
  - `find_file` 返回 `None`。
  - `load_file_content` 返回 `None`。
  - `load_core_config` 配置不存在时返回空字典（不抛出异常）。
  - `discover_strategies` / `discover_tags` 目录不存在时返回空列表。

---

## 9. 测试设计

### **API契约测试**

- **test_api.py：** 测试所有16个核心API的契约（参数、返回值、异常）。
- **测试分组：**
  - 路径核心 API（10个测试）
  - 配置核心 API（7个测试）
  - 发现核心 API（6个测试）
  - 文件核心 API（8个测试）
  - 元数据核心 API（4个测试）
  - 缓存管理 API（2个测试）
  - 边缘case测试（6个测试）
  - 契约验证（3个测试）

### **三者一致性**

- **api.py：** 定义16个抽象API。
- **api.yaml：** 定义16个API契约。
- **test_api.py：** 测试16个API。
- **确保三者完全一致。**

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [决策记录](./DECISIONS.md)
- [API契约](../api.yaml)