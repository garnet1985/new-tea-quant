# Strategy 模块单元测试用例文档

本文档记录了 Strategy 模块的所有主要测试用例，用于快速了解测试覆盖范围和测试内容。

## 📋 测试文件概览

| 测试文件 | 测试类 | 测试用例数 | 说明 |
|---------|--------|-----------|------|
| `test_version_manager.py` | `TestVersionManager` | 11 | VersionManager 版本管理测试 |
| `test_enumerator_settings.py` | `TestOpportunityEnumeratorSettings` | 12 | OpportunityEnumeratorSettings 设置验证测试 |
| `test_opportunity_enumerator.py` | `TestOpportunityEnumerator` | 6 | OpportunityEnumerator 枚举器测试 |
| `test_enumerator_worker.py` | `TestOpportunityEnumeratorWorker` | 4 | OpportunityEnumeratorWorker Worker 测试 |
| `test_result_path_manager.py` | `TestResultPathManager` | 7 | ResultPathManager 路径管理测试 |
| `test_performance_profiler.py` | `TestPerformanceProfiler`, `TestPerformanceMetrics`, `TestAggregateProfiler` | 8 | PerformanceProfiler 性能分析测试 |
| `test_path_manager_integration.py` | `TestPathManagerStrategyAPI` | 7 | PathManager Strategy API 集成测试 |
| **总计** | - | **55** | - |

---

## 1. TestVersionManager (VersionManager 测试)

### 1.1 枚举器版本管理测试

#### `test_create_enumerator_version_first_time`
- **目的**: 测试创建枚举器版本（首次创建）
- **验证点**:
  - 版本 ID 从 1 开始
  - 版本目录正确创建
  - meta.json 正确生成和更新

#### `test_create_enumerator_version_incremental`
- **目的**: 测试创建枚举器版本（递增版本号）
- **验证点**:
  - 从现有 meta.json 读取 next_version_id
  - 版本号正确递增
  - meta.json 正确更新

#### `test_create_enumerator_version_output_mode`
- **目的**: 测试创建枚举器版本（output 模式）
- **验证点**:
  - use_sampling=False 时使用 output 目录
  - meta.json 中 mode 字段正确

### 1.2 版本解析测试

#### `test_resolve_enumerator_version_latest`
- **目的**: 测试解析枚举器版本（latest）
- **验证点**:
  - 正确返回最新的版本目录
  - 支持 test/latest 格式

#### `test_resolve_enumerator_version_specific`
- **目的**: 测试解析枚举器版本（指定版本号）
- **验证点**:
  - 正确解析 test/3 格式
  - 返回正确的版本目录

#### `test_resolve_enumerator_version_default_output`
- **目的**: 测试解析枚举器版本（默认使用 output 目录）
- **验证点**:
  - 不指定目录时默认使用 output
  - 正确解析版本号

#### `test_resolve_enumerator_version_not_found`
- **目的**: 测试解析枚举器版本（版本不存在）
- **验证点**:
  - 版本不存在时抛出 FileNotFoundError

### 1.3 模拟器版本管理测试

#### `test_create_price_factor_version`
- **目的**: 测试创建价格因子模拟器版本
- **验证点**:
  - 版本目录正确创建
  - meta.json 正确生成

#### `test_resolve_price_factor_version_latest`
- **目的**: 测试解析价格因子模拟器版本（latest）
- **验证点**:
  - 正确返回最新版本

#### `test_create_capital_allocation_version`
- **目的**: 测试创建资金分配模拟器版本
- **验证点**:
  - 版本目录正确创建

#### `test_resolve_capital_allocation_version_latest`
- **目的**: 测试解析资金分配模拟器版本（latest）
- **验证点**:
  - 正确返回最新版本

#### `test_resolve_output_version`
- **目的**: 测试解析输出版本（通用方法）
- **验证点**:
  - 正确返回版本目录和子目录

---

## 2. TestOpportunityEnumeratorSettings (设置验证测试)

### 2.1 基本创建测试

#### `test_from_raw_basic`
- **目的**: 测试从原始 settings 创建（基本配置）
- **验证点**:
  - 成功创建 OpportunityEnumeratorSettings
  - 基本字段正确设置

#### `test_from_base_settings`
- **目的**: 测试从 StrategySettings 创建
- **验证点**:
  - 正确从 StrategySettings 转换

### 2.2 配置验证测试

#### `test_from_raw_missing_base_price_source`
- **目的**: 测试缺少 base_price_source
- **验证点**:
  - 抛出 ValueError

#### `test_from_raw_missing_adjust_type`
- **目的**: 测试缺少 adjust_type
- **验证点**:
  - 抛出 ValueError

#### `test_from_raw_missing_goal`
- **目的**: 测试缺少 goal 配置
- **验证点**:
  - 抛出 ValueError（goal 是必需的）

### 2.3 默认值测试

#### `test_from_raw_default_min_required_records`
- **目的**: 测试默认 min_required_records
- **验证点**:
  - 默认值为 100

#### `test_from_raw_default_indicators`
- **目的**: 测试默认 indicators
- **验证点**:
  - 默认值为空字典

#### `test_from_raw_use_sampling_default`
- **目的**: 测试 use_sampling 默认值
- **验证点**:
  - 默认值为 True

#### `test_from_raw_use_sampling_explicit`
- **目的**: 测试 use_sampling 显式设置
- **验证点**:
  - 正确读取配置值

#### `test_max_test_versions_default`
- **目的**: 测试 max_test_versions 默认值
- **验证点**:
  - 默认值为 10

#### `test_max_output_versions_default`
- **目的**: 测试 max_output_versions 默认值
- **验证点**:
  - 默认值为 3

#### `test_max_workers_default`
- **目的**: 测试 max_workers 默认值
- **验证点**:
  - 默认值为 "auto"

#### `test_to_dict`
- **目的**: 测试导出为字典
- **验证点**:
  - 保留原始字段
  - 枚举器配置正确写入

---

## 3. TestOpportunityEnumerator (枚举器测试)

### 3.1 基本流程测试

#### `test_enumerate_basic`
- **目的**: 测试枚举基本流程
- **验证点**:
  - 正确调用 VersionManager
  - 正确创建版本目录
  - 返回正确的结果格式

#### `test_load_strategy_settings`
- **目的**: 测试加载策略设置
- **验证点**:
  - 正确从模块加载 settings
  - 返回 StrategySettings 对象

### 3.2 结果保存测试

#### `test_save_results`
- **目的**: 测试保存结果
- **验证点**:
  - metadata.json 正确创建
  - 包含所有必要字段
  - is_full_enumeration 正确设置

### 3.3 版本清理测试

#### `test_cleanup_old_versions`
- **目的**: 测试清理旧版本
- **验证点**:
  - 正确保留最新的 N 个版本
  - 正确删除旧版本

#### `test_cleanup_old_versions_no_metadata`
- **目的**: 测试清理旧版本（无 metadata 文件）
- **验证点**:
  - 从目录名解析版本 ID
  - 正确清理

#### `test_cleanup_old_versions_insufficient_versions`
- **目的**: 测试清理旧版本（版本数不足）
- **验证点**:
  - 版本数不足时不删除任何版本

---

## 4. TestOpportunityEnumeratorWorker (Worker 测试)

### 4.1 初始化测试

#### `test_init`
- **目的**: 测试 Worker 初始化
- **验证点**:
  - 正确提取基本信息
  - DataManager 正确初始化

#### `test_get_date_before`
- **目的**: 测试日期计算
- **验证点**:
  - 正确计算之前的日期
  - 返回正确格式

### 4.2 运行测试

#### `test_run_no_klines`
- **目的**: 测试 run 方法（无 K 线数据）
- **验证点**:
  - 无数据时返回 success=True, opportunity_count=0

#### `test_run_with_klines_no_opportunities`
- **目的**: 测试 run 方法（有 K 线但无机会）
- **验证点**:
  - 正确处理无机会的情况

#### `test_save_stock_results`
- **目的**: 测试保存股票结果
- **验证点**:
  - CSV 文件正确创建
  - opportunities 和 targets 文件都存在

---

## 5. TestResultPathManager (路径管理测试)

### 5.1 目录管理测试

#### `test_ensure_root`
- **目的**: 测试 ensure_root 方法
- **验证点**:
  - 目录正确创建
  - 幂等性（多次调用不报错）

### 5.2 文件路径测试

#### `test_session_summary_path`
- **目的**: 测试会话级 summary 路径
- **验证点**:
  - 文件名正确

#### `test_trades_path`
- **目的**: 测试交易记录路径
- **验证点**:
  - 文件名正确

#### `test_equity_timeseries_path`
- **目的**: 测试权益时间序列路径
- **验证点**:
  - 文件名正确

#### `test_strategy_summary_path`
- **目的**: 测试策略汇总路径
- **验证点**:
  - 文件名正确

#### `test_metadata_path`
- **目的**: 测试 metadata 路径
- **验证点**:
  - 文件名正确

#### `test_stock_json_path`
- **目的**: 测试单股票 JSON 路径
- **验证点**:
  - 文件名格式正确

---

## 6. TestPerformanceProfiler (性能分析测试)

### 6.1 基本性能分析测试

#### `test_profiler_basic`
- **目的**: 测试基本性能分析
- **验证点**:
  - 计时器正确工作
  - 时间统计正确

#### `test_profiler_multiple_timers`
- **目的**: 测试多个计时器
- **验证点**:
  - 多个计时器独立工作
  - 时间正确累计

### 6.2 IO 统计测试

#### `test_profiler_db_queries`
- **目的**: 测试数据库查询计数
- **验证点**:
  - 查询次数正确
  - 查询时间正确累计

#### `test_profiler_file_writes`
- **目的**: 测试文件写入计数
- **验证点**:
  - 写入次数正确
  - 文件大小正确累计

#### `test_profiler_memory_tracking`
- **目的**: 测试内存跟踪
- **验证点**:
  - 内存使用正确记录

### 6.3 Metrics 测试

#### `test_metrics_to_dict`
- **目的**: 测试 metrics 转换为字典
- **验证点**:
  - 字典结构正确
  - 所有字段正确转换

### 6.4 聚合分析测试

#### `test_aggregate_profiler_add_stock`
- **目的**: 测试添加股票指标
- **验证点**:
  - 指标正确添加
  - 可以正确检索

#### `test_aggregate_profiler_get_summary`
- **目的**: 测试获取汇总统计
- **验证点**:
  - 正确聚合多个股票的指标
  - 计算平均值正确

#### `test_aggregate_profiler_empty`
- **目的**: 测试空汇总
- **验证点**:
  - 无数据时返回空字典

---

## 7. TestPathManagerStrategyAPI (PathManager API 集成测试)

### 7.1 API 功能测试

#### `test_strategy_opportunity_enums_test_mode`
- **目的**: 测试枚举器结果目录（test 模式）
- **验证点**:
  - 路径正确
  - 目录名为 test

#### `test_strategy_opportunity_enums_output_mode`
- **目的**: 测试枚举器结果目录（output 模式）
- **验证点**:
  - 路径正确
  - 目录名为 output

#### `test_strategy_simulations_price_factor`
- **目的**: 测试价格因子模拟器结果目录
- **验证点**:
  - 路径正确

#### `test_strategy_capital_allocation`
- **目的**: 测试资金分配模拟器结果目录
- **验证点**:
  - 路径正确

#### `test_strategy_scan_cache`
- **目的**: 测试扫描缓存目录
- **验证点**:
  - 路径正确

#### `test_strategy_scan_results`
- **目的**: 测试扫描结果目录
- **验证点**:
  - 路径正确

#### `test_strategy_api_consistency`
- **目的**: 测试 API 一致性
- **验证点**:
  - 所有 API 都基于 strategy_results
  - 路径结构一致

---

## 📊 测试覆盖统计

### 按功能模块分类

| 功能模块 | 测试用例数 | 覆盖率 |
|---------|-----------|--------|
| **版本管理** | 11 | 核心功能全覆盖 |
| **设置验证** | 12 | 核心功能全覆盖 |
| **枚举器** | 6 | 基础功能覆盖 |
| **Worker** | 4 | 基础功能覆盖 |
| **路径管理** | 7 | 核心功能全覆盖 |
| **性能分析** | 8 | 核心功能全覆盖 |
| **API 集成** | 7 | 核心功能全覆盖 |
| **总计** | **55** | - |

### 按测试类型分类

| 测试类型 | 测试用例数 | 说明 |
|---------|-----------|------|
| **创建和初始化** | 8 | 测试对象创建和初始化 |
| **配置验证** | 5 | 测试配置有效性验证 |
| **业务逻辑** | 12 | 测试核心业务逻辑 |
| **路径管理** | 14 | 测试路径构建和文件操作 |
| **边界条件** | 16 | 测试异常和边界情况 |

---

## 🔍 测试重点

### 1. 版本管理
- ✅ 版本目录创建
- ✅ 版本号递增
- ✅ 版本解析（latest、指定版本）
- ✅ meta.json 管理

### 2. 设置验证
- ✅ 必需字段验证
- ✅ 默认值补全
- ✅ 配置导出

### 3. 枚举器流程
- ✅ 基本枚举流程
- ✅ 结果保存
- ✅ 版本清理

### 4. Worker 功能
- ✅ 初始化
- ✅ 数据加载
- ✅ 结果保存

### 5. 路径管理
- ✅ PathManager API
- ✅ ResultPathManager
- ✅ 路径一致性

### 6. 性能分析
- ✅ 时间统计
- ✅ IO 统计
- ✅ 内存跟踪
- ✅ 聚合分析

---

## 📝 测试运行说明

### 运行所有测试
```bash
# 使用 pytest
pytest core/modules/strategy/__test__/

# 或使用 Python unittest
python -m pytest core/modules/strategy/__test__/
```

### 运行特定测试文件
```bash
pytest core/modules/strategy/__test__/test_version_manager.py
```

### 运行特定测试类
```bash
pytest core/modules/strategy/__test__/test_version_manager.py::TestVersionManager
```

### 运行特定测试方法
```bash
pytest core/modules/strategy/__test__/test_version_manager.py::TestVersionManager::test_create_enumerator_version_first_time
```

---

## 🔄 更新记录

- **2026-01-17**: 初始版本，包含 55 个测试用例
  - VersionManager: 11 个测试用例
  - OpportunityEnumeratorSettings: 12 个测试用例
  - OpportunityEnumerator: 6 个测试用例
  - OpportunityEnumeratorWorker: 4 个测试用例
  - ResultPathManager: 7 个测试用例
  - PerformanceProfiler: 8 个测试用例
  - PathManager API: 7 个测试用例

---

## 📌 注意事项

1. **Mock 使用**: 大部分测试使用 mock 来隔离外部依赖（DataManager、文件系统等）
2. **临时目录**: 使用临时目录进行文件操作测试，测试后自动清理
3. **边界条件**: 重点关注边界条件和错误处理
4. **配置验证**: 详细测试配置验证逻辑，确保无效配置被正确拒绝
5. **路径一致性**: 确保所有路径 API 的一致性
