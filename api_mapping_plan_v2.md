# ProjectContext API 分层映射计划（v2 - 根据用户feedback调整）

## 一、核心理念

**ProjectContext = 项目快捷入口**
- 没有ProjectContext不block任何开发
- 用户可以自己拼凑/使用底层模块的API来做到想做的事情
- ProjectContext只暴露真正"项目快捷"的API，不包含所有底层能力

**底层模块 = 提供基础能力**
- 高级用户可以直接使用底层模块
- ProjectContext可以调用底层模块，但不是所有底层能力都要暴露到ProjectContext

---

## 二、重新理解分层

| 层级 | 模块 | 说明 | 使用对象 |
|------|------|------|---------|
| **底层** | infra/discovery、infra/file、PathManager、ConfigManager | 提供基础能力（find_file、load_file_content、deep_merge等） | 高级用户、ProjectContext等应用层模块 |
| **应用层** | ProjectContext | 封装项目快捷API（discover_strategies、load_data_config等） | 普通用户、业务代码 |

---

## 三、应该保留在ProjectContext的API（约18-20个）

### 3.1 ProjectContext.path（约10个）

只保留真正"项目快捷"的路径API：

```python
ProjectContext.path.get_project_root()                      # 项目根目录 - 快捷
ProjectContext.path.get_userspace_root()                    # userspace目录 - 快捷
ProjectContext.path.get_strategies_root()                   # 策略根目录 - 快捷
ProjectContext.path.get_tags_root()                         # Tag根目录 - 快捷
ProjectContext.path.get_system_db_directory()               # 系统数据库目录 - 快捷
ProjectContext.path.get_strategy_directory(strategy_name)   # 策略目录 - 快捷
ProjectContext.path.get_tag_scenario_directory(scenario_name) # Tag目录 - 快捷
ProjectContext.path.get_data_contract_root()                # data contract根目录 - 快捷
ProjectContext.path.get_extensions_tables_directory()       # extensions tables目录 - 快捷
ProjectContext.path.clear_userspace_cache()                 # 清理缓存 - 快捷操作
```

**删除的API（太细或太底层）：**
- get_core_root, get_extensions_root, get_system_root - 太细
- get_default_config_root, get_user_config_root - 配置层自己处理
- get_backup_directory, get_updater_directory, get_userspace_tmp_directory, get_userspace_ntq_directory - 太细
- get_strategy_settings_path, get_strategy_results_directory - 太细，自己拼路径
- get_strategy_simulation_price_directory, get_strategy_simulation_capital_directory, get_strategy_simulation_enum_directory, get_strategy_scan_results_directory - 太细
- get_tag_scenario_settings_path, get_tag_scenario_worker_path - 太细
- get_data_source_root, get_data_source_mapping_path, get_data_source_handlers_directory, get_data_source_handler_directory, get_data_source_providers_directory, get_data_source_provider_directory - 太细或太底层
- get_data_contract_mapping_path, get_data_contract_loaders_directory, get_adapters_directory - 太细

---

### 3.2 ProjectContext.config（约6个）

只保留真正"项目快捷"的配置API：

```python
ProjectContext.config.load_data_config()                    # 加载data.json - 快捷
ProjectContext.config.load_database_config(database_type)   # 加载数据库配置 - 快捷
ProjectContext.config.get_default_start_date()              # 默认开始日期 - 快捷
ProjectContext.config.get_as_of_latest_completed_trading_date() # as_of日期 - 快捷
ProjectContext.config.get_use_sample_stock_list()           # 样本股票池规模 - 快捷
ProjectContext.config.load_overridable_config(domain, config_id) # 加载可覆盖配置 - 快捷
```

**删除的API（底层工具）：**
- load_with_defaults, deep_merge_config, merge_mapping_configs - 底层合并工具，应该在ConfigManager
- load_json_file, parse_python_config, load_with_env_vars - 底层加载工具，应该在ConfigManager
- load_benchmark_stock_index_list - 太细，可以自己从load_data_config()获取

---

### 3.3 ProjectContext.discovery（约3个）

只保留真正"项目快捷"的发现API：

```python
ProjectContext.discovery.discover_strategies()              # 发现策略 - 快捷
ProjectContext.discovery.discover_tags()                    # 发现Tag - 快捷
ProjectContext.discovery.discover_configs(domain)           # 发现配置 - 快捷
```

**删除的API（应该在底层模块）：**
- find_file(filename, search_dir) - 应该在 infra/discovery（底层文件发现工具）
- find_in_tree(base_dir, key, filename) - 应该在 infra/discovery（底层目录树发现工具）
- discover_config(domain, config_id) - 太底层

---

### 3.4 ProjectContext.file（应该删除，移到底层）

**所有文件API都应该在底层模块，不应该在ProjectContext：**

```python
# 应该在 infra/discovery 或 infra/file（底层）
find_file(filename, search_dir, recursive)
load_file_content(path, encoding)
```

**理由：**
- find_file、load_file_content 是底层工具，不是项目快捷API
- 高级用户可以直接使用 infra/discovery.find_file()
- ProjectContext不应该包含所有底层能力

---

### 3.5 ProjectContext.meta（约2个）

```python
ProjectContext.meta.core_version()                          # core版本 - 快捷
ProjectContext.meta.core_info()                             # core信息 - 快捷
```

---

## 四、总计

| 命名空间 | API数量 | 说明 |
|---------|---------|------|
| path | 10 | 项目快捷路径 |
| config | 6 | 项目快捷配置 |
| discovery | 3 | 项目快捷发现 |
| file | 0 | 全部移到底层模块 |
| meta | 2 | 项目快捷元数据 |
| **总计** | **21** | |

从63个精简到21个，删除了42个过于底层或太细的API。

---

## 五、应该在底层模块的API（约40个）

| API | 应该在哪个底层模块 | 说明 |
|-----|------------------|------|
| find_file(filename, search_dir) | infra/discovery | 底层文件发现工具 |
| load_file_content(path) | infra/discovery 或 infra/file | 底层文件加载工具 |
| find_in_tree(base_dir, key) | infra/discovery | 底层目录树发现工具 |
| deep_merge_config(...) | ConfigManager | 底层配置合并工具 |
| load_json_file(path) | ConfigManager | 底层JSON加载工具 |
| parse_python_config(path) | ConfigManager | 底层Python配置解析 |
| load_with_env_vars(...) | ConfigManager | 底层环境变量覆盖 |
| get_default_config_root() | PathManager | 内部路径 |
| get_user_config_root() | PathManager | 内部路径 |
| get_strategy_settings_path(strategy_name) | PathManager | 太细，自己拼路径 |
| ... 其他过于细节的路径API | PathManager | 太细 |

---

## 六、执行计划（零破坏，安全）

### Phase 1：添加命名空间API（保留所有平铺API）

**原则：零破坏，不删除任何API**

- 只添加命名空间API，不删除任何API
- 所有平铺API保留，作为proxy调用命名空间方法
- 完全零破坏，现有代码不需要改动

**实现方式：**
```python
class ProjectContext:
    class path:
        @staticmethod
        def get_project_root() -> Path:
            return PathManager.get_project_root()
    
    # 平铺API保留为proxy
    @staticmethod
    def get_project_root() -> Path:
        return ProjectContext.path.get_project_root()
```

---

### Phase 2：逐个迁移调用方（不批量）

**原则：一个一个API迁移，不批量改动**

- 一个一个API迁移，不批量改动
- 每迁移一个API就运行测试验证
- 发现问题立即回退

**迁移顺序：**
1. 先迁移最常用的API（get_project_root、load_data_config等）
2. 再迁移次常用的API
3. 最后迁移很少用的API

---

### Phase 3：确认所有迁移完成后再考虑删除

**原则：等所有调用方都确认迁移完毕**

- 等所有调用方都确认迁移完毕
- 再考虑是否删除平铺API
- 甚至可以永远保留平铺API作为向后兼容

---

## 七、需要确认

请确认以下几点：

1. **这个理念是否认同？** ProjectContext = 项目快捷入口，不包含所有底层能力？
2. **这个映射表是否合理？** 21个API，删除了42个过于底层或太细的API？
3. **file命名空间是否应该删除？** find_file、load_file_content 移到 infra/discovery？
4. **执行计划是否安全？** 先添加命名空间（保留平铺），再逐个迁移，最后考虑删除？

确认后我就开始执行Phase 1（添加命名空间API，零破坏）。