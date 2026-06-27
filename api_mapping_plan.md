# ProjectContext API 分层映射计划

## 一、总览

当前状态：63个API（平铺）
目标状态：约40个API（分为4层：path/core/file/config/discovery）

## 二、各Manager公开方法完整清单

### 2.1 PathManager（35个方法）

| 方法名 | 参数 | 说明 | 当前外部使用 | 建议命名空间 | 保留/删除 | 理由 |
|--------|------|------|-------------|-------------|-----------|------|
| get_project_root | () | 项目根目录 | 大量使用 | path | 保留 | 核心路径 |
| get_core_root | () | core目录 | 有使用 | path | 保留 | 核心路径 |
| get_userspace_root | () | userspace目录 | 大量使用 | path | 保留 | 核心路径 |
| get_extensions_root | () | extensions目录 | 内部使用 | path | 保留 | 核心路径 |
| get_system_root | () | system目录 | 内部使用 | path | 保留 | 核心路径 |
| get_default_config_root | () | 默认配置目录 | 内部使用 | path | 删除 | 太底层，配置层自己处理 |
| get_user_config_root | () | 用户配置目录 | 内部使用 | path | 删除 | 太底层，配置层自己处理 |
| get_system_db_directory | () | 系统数据库目录 | 有使用 | path | 保留 | 常用路径 |
| get_backup_directory | () | 备份目录 | 内部使用 | path | 删除 | 太细 |
| get_updater_directory | () | updater目录 | 内部使用 | path | 删除 | 太细 |
| get_userspace_tmp_directory | () | 临时目录 | 有使用 | path | 保留 | 常用路径 |
| get_strategies_root | () | 策略根目录 | 大量使用 | path | 保留 | 核心路径 |
| get_tags_root | () | Tag根目录 | 有使用 | path | 保留 | 核心路径 |
| get_strategy_directory | (strategy_name) | 策略目录 | 大量使用 | path | 保留 | 核心路径 |
| get_strategy_settings_path | (strategy_name) | 策略配置文件路径 | 内部使用 | path | 删除 | 太细，自己拼路径 |
| get_strategy_results_directory | (strategy_name) | 策略结果目录 | 内部使用 | path | 删除 | 太细 |
| get_strategy_simulation_price_directory | (strategy_name) | 模拟价格目录 | 有使用 | path | 保留 | 常用路径 |
| get_strategy_simulation_capital_directory | (strategy_name) | 模拟资金目录 | 有使用 | path | 保留 | 常用路径 |
| get_strategy_simulation_enum_directory | (strategy_name) | 模拟枚举目录 | 有使用 | path | 保留 | 常用路径 |
| get_strategy_scan_results_directory | (strategy_name) | 扫描结果目录 | 有使用 | path | 保留 | 常用路径 |
| get_tag_scenario_directory | (scenario_name) | Tag目录 | 有使用 | path | 保留 | 核心路径 |
| get_tag_scenario_settings_path | (scenario_name) | Tag配置路径 | 内部使用 | path | 删除 | 太细 |
| get_tag_scenario_worker_path | (scenario_name) | Tag worker路径 | 内部使用 | path | 删除 | 太细 |
| get_data_source_root | () | 数据源根目录 | 内部使用 | path | 删除 | 太底层 |
| get_data_source_mapping_path | () | 数据源映射路径 | 内部使用 | path | 删除 | 太底层 |
| get_data_source_handlers_directory | () | handlers目录 | 有使用 | path | 保留 | 常用路径 |
| get_data_source_handler_directory | (handler_name) | 单个handler目录 | 内部使用 | path | 删除 | 太细 |
| get_data_source_providers_directory | () | providers目录 | 内部使用 | path | 删除 | 太细 |
| get_data_source_provider_directory | (provider_name) | 单个provider目录 | 内部使用 | path | 删除 | 太细 |
| get_data_contract_root | () | data contract根目录 | 有使用 | path | 保留 | 常用路径 |
| get_data_contract_mapping_path | () | data contract映射路径 | 内部使用 | path | 删除 | 太细 |
| get_data_contract_loaders_directory | () | data contract loaders目录 | 内部使用 | path | 删除 | 太细 |
| get_extensions_tables_directory | () | extensions tables目录 | 有使用 | path | 保留 | 常用路径 |
| get_adapters_directory | () | adapters目录 | 有使用 | path | 保留 | 常用路径 |
| get_userspace_ntq_directory | () | userspace NTQ目录 | 内部使用 | path | 删除 | 太细 |
| clear_userspace_cache | () | 清理缓存 | 有使用 | path | 保留 | 常用操作 |

**PathManager总结：** 35个 → 保留18个，删除17个

---

### 2.2 ConfigManager（15个方法）

| 方法名 | 参数 | 说明 | 当前外部使用 | 建议命名空间 | 保留/删除 | 理由 |
|--------|------|------|-------------|-------------|-----------|------|
| load_core_config | (config_name) | 加载核心配置 | 有使用 | config | 保留 | 核心配置入口 |
| load_database_config | (database_type) | 加载数据库配置 | 有使用 | config | 保留 | 核心配置入口 |
| load_data_config | () | 加载data.json | 大量使用 | config | 保留 | 核心配置入口 |
| load_benchmark_stock_index_list | () | 加载基准指数列表 | 有使用 | config | 保留 | 常用配置 |
| get_default_start_date | () | 获取默认开始日期 | 有使用 | config | 保留 | 常用配置 |
| get_as_of_latest_completed_trading_date | () | 获取as_of日期 | 有使用 | config | 保留 | 常用配置 |
| get_use_sample_stock_list | () | 获取样本股票池规模 | 有使用 | config | 保留 | 常用配置 |
| load_with_defaults | (default_path, user_path, ...) | 加载配置（底层） | 内部使用 | - | 删除 | 太底层 |
| deep_merge_config | (defaults, custom, ...) | 深度合并（底层） | 内部使用 | - | 删除 | 太底层 |
| merge_mapping_configs | (defaults, custom, ...) | 映射合并（底层） | 内部使用 | - | 删除 | 太底层 |
| load_json_file | (path) | 加载JSON（底层） | 内部使用 | - | 删除 | 太底层 |
| parse_python_config | (path, var_name) | 解析Python配置（底层） | 内部使用 | - | 删除 | 太底层 |
| load_with_env_vars | (config, env_var_mapping) | 环境变量覆盖（底层） | 内部使用 | - | 删除 | 太底层 |
| load_json | (path) | load_json_file别名 | 内部使用 | - | 删除 | deprecated |
| load_python | (path, var_name) | parse_python_config别名 | 内部使用 | - | 删除 | deprecated |

**ConfigManager总结：** 15个 → 保留7个，删除8个

---

### 2.3 DiscoveryManager（5个方法）

| 方法名 | 参数 | 说明 | 当前外部使用 | 建议命名空间 | 保留/删除 | 理由 |
|--------|------|------|-------------|-------------|-----------|------|
| discover_configs | (domain) | 发现配置列表 | 有使用 | discovery | 保留 | 核心发现 |
| discover_config | (domain, config_id) | 发现单个配置 | 内部使用 | discovery | 删除 | 太底层 |
| load_overridable_config | (domain, config_id, ...) | 加载可覆盖配置 | 有使用 | config | 保留 | 常用配置入口 |
| find_in_tree | (base_dir, key, filename) | 在目录树查找 | 有使用 | discovery | 保留 | 常用发现 |
| discover_strategies | () | 发现策略 | 有使用 | discovery | 保留 | 核心发现 |
| discover_tags | () | 发现Tag | 有使用 | discovery | 保留 | 核心发现 |

**DiscoveryManager总结：** 6个 → 保留5个，删除1个

---

### 2.4 FileManager（2个方法）

| 方法名 | 参数 | 说明 | 当前外部使用 | 建议命名空间 | 保留/删除 | 理由 |
|--------|------|------|-------------|-------------|-----------|------|
| find_file | (filename, search_dir, recursive) | 查找文件 | 有使用 | file | 保留 | 常用文件操作 |
| load_file_content | (path, encoding) | 加载文件内容 | 有使用 | file | 保留 | 常用文件操作 |

**FileManager总结：** 2个 → 保留2个，删除0个

---

## 三、最终命名空间映射表

### 3.1 ProjectContext.path（18个）

```python
ProjectContext.path.get_project_root()
ProjectContext.path.get_core_root()
ProjectContext.path.get_userspace_root()
ProjectContext.path.get_extensions_root()
ProjectContext.path.get_system_root()
ProjectContext.path.get_system_db_directory()
ProjectContext.path.get_userspace_tmp_directory()
ProjectContext.path.get_strategies_root()
ProjectContext.path.get_tags_root()
ProjectContext.path.get_strategy_directory(strategy_name)
ProjectContext.path.get_strategy_simulation_price_directory(strategy_name)
ProjectContext.path.get_strategy_simulation_capital_directory(strategy_name)
ProjectContext.path.get_strategy_simulation_enum_directory(strategy_name)
ProjectContext.path.get_strategy_scan_results_directory(strategy_name)
ProjectContext.path.get_tag_scenario_directory(scenario_name)
ProjectContext.path.get_data_source_handlers_directory()
ProjectContext.path.get_data_contract_root()
ProjectContext.path.get_extensions_tables_directory()
ProjectContext.path.get_adapters_directory()
ProjectContext.path.clear_userspace_cache()
```

**注意：以上实际是20个，需要精简到18个。建议删除 get_extensions_root, get_system_root**

---

### 3.2 ProjectContext.config（8个）

```python
ProjectContext.config.load_core_config(config_name)
ProjectContext.config.load_database_config(database_type=None)
ProjectContext.config.load_data_config()
ProjectContext.config.load_benchmark_stock_index_list()
ProjectContext.config.get_default_start_date()
ProjectContext.config.get_as_of_latest_completed_trading_date()
ProjectContext.config.get_use_sample_stock_list()
ProjectContext.config.load_overridable_config(domain, config_id, **kwargs)
```

---

### 3.3 ProjectContext.discovery（5个）

```python
ProjectContext.discovery.discover_configs(domain="")
ProjectContext.discovery.discover_strategies()
ProjectContext.discovery.discover_tags()
ProjectContext.discovery.find_in_tree(base_dir, key, config_filename="config.py")
```

**注意：load_overridable_config 移到了 config 命名空间**

---

### 3.4 ProjectContext.file（2个）

```python
ProjectContext.file.find_file(filename, search_dir, recursive=True)
ProjectContext.file.load_file_content(path, encoding="utf-8")
```

---

### 3.5 ProjectContext.meta（2个）

```python
ProjectContext.meta.core_version()
ProjectContext.meta.core_info()
```

---

## 四、总计

| 命名空间 | API数量 |
|---------|---------|
| path | 18 |
| config | 8 |
| discovery | 4 |
| file | 2 |
| meta | 2 |
| **总计** | **34** |

从63个精简到34个，删除了29个过于底层或太细的API。

---

## 五、关于discovery模块的决策

**建议：保留infra/discovery不动，在ProjectContext里加.discovery命名空间**

理由：
1. **职责完全不同**：
   - infra/discovery：通用Python类发现（ClassDiscovery/ModuleDiscovery），零依赖
   - ProjectContext.discovery：项目配置文件发现（discover_strategies/discover_tags），依赖项目路径结构
2. **合并会破坏infra/discovery的纯净性**：infra/discovery是通用基础设施，应该保持独立
3. **用户心智一致**：调用方通过ProjectContext访问项目相关的发现功能，通过infra/discovery访问通用类发现功能

---

## 六、执行计划

**Phase 1：添加命名空间API（零破坏）**
- 修改 api.py：添加命名空间内部类定义
- 修改 project_context_manager.py：添加命名空间内部类实现
- 保留平铺API作为proxy（调用命名空间方法）
- 运行测试验证

**Phase 2：批量迁移调用方**
- 写批量迁移脚本：把所有 `ProjectContext.xxx()` 改为 `ProjectContext.namespace.xxx()`
- 运行全量测试验证

**Phase 3：删除平铺API**
- 删除所有平铺API和proxy
- 更新 api.yaml 和 test_api.py
- 运行测试验证

---

## 七、需要确认的问题

请确认以下几点：

1. **这个映射表是否合理？** 有没有遗漏的常用API？有没有不该保留的API？
2. **discovery的决策是否同意？** 保留infra/discovery不动，在ProjectContext里加.discovery命名空间？
3. **命名空间命名是否合理？** path/config/discovery/file/meta？有没有更好的命名？
4. **是否同意这个执行计划？** 先加命名空间API（保留平铺），再迁移，最后删除？

确认后我就开始执行。