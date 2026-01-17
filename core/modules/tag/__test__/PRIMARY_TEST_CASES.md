# Tag 模块单元测试用例文档

本文档记录了 Tag 模块的所有主要测试用例，用于快速了解测试覆盖范围和测试内容。

## 📋 测试文件概览

| 测试文件 | 测试类 | 测试用例数 | 说明 |
|---------|--------|-----------|------|
| `test_scenario_model.py` | `TestScenarioModel` | 18 | ScenarioModel 模型测试 |
| `test_tag_model.py` | `TestTagModel` | 13 | TagModel 模型测试 |
| `test_tag_helper.py` | `TestTagHelper` | 9 | TagHelper 辅助函数测试 |
| `test_job_helper.py` | `TestJobHelper` | 9 | JobHelper 任务辅助函数测试 |
| `test_tag_manager.py` | `TestTagManager` | 8 | TagManager 核心管理器测试 |
| **总计** | - | **57** | - |

---

## 1. TestScenarioModel (ScenarioModel 测试)

### 1.1 创建和初始化测试

#### `test_create_from_settings_basic`
- **目的**: 测试从 settings 创建 ScenarioModel（基本配置）
- **验证点**:
  - 成功创建 ScenarioModel 实例
  - name、target_entity、is_enabled 正确设置
  - tag_models 正确加载（数量、名称）

#### `test_create_from_settings_with_display_name`
- **目的**: 测试从 settings 创建 ScenarioModel（带 display_name）
- **验证点**:
  - display_name 和 description 正确设置

#### `test_create_from_settings_default_display_name`
- **目的**: 测试从 settings 创建 ScenarioModel（默认 display_name）
- **验证点**:
  - 当没有提供 display_name 时，使用 name 作为默认值

#### `test_create_from_settings_target_entity_string`
- **目的**: 测试从 settings 创建 ScenarioModel（target_entity 为字符串，向后兼容）
- **验证点**:
  - 支持旧格式的 target_entity（字符串类型）

### 1.2 配置验证测试

#### `test_is_setting_valid_valid`
- **目的**: 测试 is_setting_valid（有效配置）
- **验证点**:
  - 完整有效的配置返回 True

#### `test_is_setting_valid_missing_target_entity`
- **目的**: 测试 is_setting_valid（缺少 target_entity）
- **验证点**:
  - 缺少必需字段时返回 False

#### `test_is_setting_valid_missing_tags`
- **目的**: 测试 is_setting_valid（缺少 tags）
- **验证点**:
  - 缺少 tags 字段时返回 False

#### `test_is_setting_valid_empty_tags`
- **目的**: 测试 is_setting_valid（tags 为空列表）
- **验证点**:
  - tags 为空列表时返回 False

#### `test_is_setting_valid_incremental_missing_required_records`
- **目的**: 测试 is_setting_valid（INCREMENTAL 模式缺少 required_records）
- **验证点**:
  - INCREMENTAL 模式下必须提供 incremental_required_records_before_as_of_date

#### `test_is_setting_valid_incremental_invalid_required_records`
- **目的**: 测试 is_setting_valid（INCREMENTAL 模式 required_records 无效）
- **验证点**:
  - required_records 必须是非负整数

### 1.3 更新模式测试

#### `test_calculate_update_mode_incremental`
- **目的**: 测试 calculate_update_mode（INCREMENTAL 模式）
- **验证点**:
  - 正确识别并返回 INCREMENTAL 模式

#### `test_calculate_update_mode_refresh`
- **目的**: 测试 calculate_update_mode（REFRESH 模式）
- **验证点**:
  - 正确识别并返回 REFRESH 模式

#### `test_calculate_update_mode_recompute`
- **目的**: 测试 calculate_update_mode（recompute=True 时返回 REFRESH）
- **验证点**:
  - recompute=True 时强制返回 REFRESH 模式

#### `test_calculate_update_mode_default`
- **目的**: 测试 calculate_update_mode（默认值）
- **验证点**:
  - 未指定时默认使用 INCREMENTAL 模式

### 1.4 数据访问测试

#### `test_get_tags_dict`
- **目的**: 测试 get_tags_dict
- **验证点**:
  - 正确返回 tags 字典，key 为 tag name

#### `test_to_dict`
- **目的**: 测试 to_dict
- **验证点**:
  - 正确序列化为字典，包含所有字段

---

## 2. TestTagModel (TagModel 测试)

### 2.1 创建和初始化测试

#### `test_create_from_settings_basic`
- **目的**: 测试从 settings 创建 TagModel（基本配置）
- **验证点**:
  - 成功创建 TagModel 实例
  - name、display_name、description 正确设置（默认值）

#### `test_create_from_settings_with_display_name`
- **目的**: 测试从 settings 创建 TagModel（带 display_name）
- **验证点**:
  - display_name 和 description 正确设置

#### `test_create_from_settings_default_display_name`
- **目的**: 测试从 settings 创建 TagModel（默认 display_name）
- **验证点**:
  - 当没有提供 display_name 时，使用 name 作为默认值

### 2.2 配置验证测试

#### `test_is_setting_valid_valid`
- **目的**: 测试 is_setting_valid（有效配置）
- **验证点**:
  - 完整有效的配置返回 True

#### `test_is_setting_valid_missing_name`
- **目的**: 测试 is_setting_valid（缺少 name）
- **验证点**:
  - 缺少 name 字段时返回 False

#### `test_is_setting_valid_empty_name`
- **目的**: 测试 is_setting_valid（name 为空）
- **验证点**:
  - name 为空字符串时返回 False

#### `test_is_setting_valid_none_name`
- **目的**: 测试 is_setting_valid（name 为 None）
- **验证点**:
  - name 为 None 时返回 False

### 2.3 数据转换测试

#### `test_from_dict`
- **目的**: 测试 from_dict（从字典创建 TagModel）
- **验证点**:
  - 正确从数据库字典恢复 TagModel 实例
  - 所有字段正确设置

#### `test_to_dict`
- **目的**: 测试 to_dict
- **验证点**:
  - 正确序列化为字典，包含所有字段

#### `test_get_settings`
- **目的**: 测试 get_settings
- **验证点**:
  - 正确返回 settings 字典

### 2.4 元数据差异测试

#### `test_has_meta_diff_different_display_name`
- **目的**: 测试 _has_meta_diff（display_name 不同）
- **验证点**:
  - 检测到 display_name 差异时返回 True

#### `test_has_meta_diff_different_description`
- **目的**: 测试 _has_meta_diff（description 不同）
- **验证点**:
  - 检测到 description 差异时返回 True

#### `test_has_meta_diff_no_diff`
- **目的**: 测试 _has_meta_diff（无差异）
- **验证点**:
  - 无差异时返回 False

---

## 3. TestTagHelper (TagHelper 测试)

### 3.1 加载 Scenario Settings 测试

#### `test_load_scenario_settings_success`
- **目的**: 测试 load_scenario_settings（成功加载）
- **验证点**:
  - 成功找到并加载 settings.py 文件
  - 正确解析 Settings 变量
  - 返回 settings_path 和 settings_dict

#### `test_load_scenario_settings_file_not_found`
- **目的**: 测试 load_scenario_settings（文件不存在）
- **验证点**:
  - 文件不存在时返回 (None, None)

#### `test_load_scenario_settings_invalid_settings`
- **目的**: 测试 load_scenario_settings（settings 无效）
- **验证点**:
  - ConfigManager 返回 None 时返回 (None, None)

#### `test_load_scenario_settings_not_dict`
- **目的**: 测试 load_scenario_settings（settings 不是字典）
- **验证点**:
  - settings 不是字典类型时返回 (None, None)

### 3.2 加载 Worker Class 测试

#### `test_load_worker_class_success`
- **目的**: 测试 load_worker_class（成功加载）
- **验证点**:
  - 成功找到并加载 tag_worker.py 文件
  - 正确识别继承自 BaseTagWorker 的类
  - 返回 worker_path 和 worker_class

#### `test_load_worker_class_file_not_found`
- **目的**: 测试 load_worker_class（文件不存在）
- **验证点**:
  - 文件不存在时返回 (None, None)

#### `test_load_worker_class_no_worker_class`
- **目的**: 测试 load_worker_class（没有 worker 类）
- **验证点**:
  - 模块中没有继承 BaseTagWorker 的类时返回 (None, None)

#### `test_load_worker_class_spec_none`
- **目的**: 测试 load_worker_class（spec 为 None）
- **验证点**:
  - spec_from_file_location 返回 None 时返回 (None, None)

#### `test_load_worker_class_loader_none`
- **目的**: 测试 load_worker_class（loader 为 None）
- **验证点**:
  - spec.loader 为 None 时返回 (None, None)

---

## 4. TestJobHelper (JobHelper 测试)

### 4.1 Worker 数量决策测试

#### `test_decide_worker_amount_100_or_less`
- **目的**: 测试 decide_worker_amount（100个及以下）
- **验证点**:
  - 100 个及以下 job 返回 1 个 worker

#### `test_decide_worker_amount_500_or_less`
- **目的**: 测试 decide_worker_amount（500个及以下，100个以上）
- **验证点**:
  - 101-500 个 job 返回 2 个 worker

#### `test_decide_worker_amount_1000_or_less`
- **目的**: 测试 decide_worker_amount（1000个及以下，500个以上）
- **验证点**:
  - 501-1000 个 job 返回 4 个 worker

#### `test_decide_worker_amount_2000_or_less`
- **目的**: 测试 decide_worker_amount（2000个及以下，1000个以上）
- **验证点**:
  - 1001-2000 个 job 返回 8 个 worker

#### `test_decide_worker_amount_over_2000`
- **目的**: 测试 decide_worker_amount（2000个以上）
- **验证点**:
  - 2000 个以上 job 返回最大 worker 数（CPU 核心数）

#### `test_decide_worker_amount_with_max_workers`
- **目的**: 测试 decide_worker_amount（指定 max_workers）
- **验证点**:
  - 指定 max_workers 时，不超过该值

#### `test_decide_worker_amount_with_auto`
- **目的**: 测试 decide_worker_amount（max_workers="auto"）
- **验证点**:
  - "auto" 模式使用 CPU 核心数

### 4.2 日期计算测试

#### `test_calculate_start_and_end_date_refresh_mode`
- **目的**: 测试 calculate_start_and_end_date（REFRESH 模式）
- **验证点**:
  - REFRESH 模式使用默认开始日期
  - 使用指定的结束日期

#### `test_calculate_start_and_end_date_incremental_mode_with_last_date`
- **目的**: 测试 calculate_start_and_end_date（INCREMENTAL 模式，有最后更新日期）
- **验证点**:
  - INCREMENTAL 模式从最后更新日期的下一个交易日开始

#### `test_calculate_start_and_end_date_incremental_mode_no_last_date`
- **目的**: 测试 calculate_start_and_end_date（INCREMENTAL 模式，无最后更新日期）
- **验证点**:
  - 无最后更新日期时使用默认开始日期

---

## 5. TestTagManager (TagManager 测试)

### 5.1 初始化测试

#### `test_init`
- **目的**: 测试 TagManager 初始化
- **验证点**:
  - 正确初始化所有属性
  - 调用 _discover_scenarios_from_folder
  - DataManager 正确初始化

#### `test_refresh_scenario`
- **目的**: 测试 refresh_scenario
- **验证点**:
  - 清空缓存
  - 重新发现 scenarios

### 5.2 执行测试

#### `test_execute_with_scenario_name`
- **目的**: 测试 execute（指定 scenario_name）
- **验证点**:
  - 调用 _execute_single 方法
  - 传入正确的 scenario_name

#### `test_execute_with_settings`
- **目的**: 测试 execute（指定 settings）
- **验证点**:
  - 调用 _execute_single_from_tmp_settings 方法
  - 传入正确的 settings

#### `test_execute_all`
- **目的**: 测试 execute（执行所有 scenarios）
- **验证点**:
  - 遍历所有 scenario_cache
  - 为每个 scenario 调用 _execute_single

### 5.3 场景发现和缓存测试

#### `test_discover_scenarios_from_folder_not_exists`
- **目的**: 测试 _discover_scenarios_from_folder（目录不存在）
- **验证点**:
  - 目录不存在时 scenario_cache 为空

#### `test_load_scenario_from_cache_by_name_exists`
- **目的**: 测试 _load_scenario_from_cache_by_name（存在）
- **验证点**:
  - 正确从缓存中加载 scenario
  - 返回正确的 settings

#### `test_load_scenario_from_cache_by_name_not_exists`
- **目的**: 测试 _load_scenario_from_cache_by_name（不存在）
- **验证点**:
  - scenario 不存在时返回 None

---

## 📊 测试覆盖统计

### 按功能模块分类

| 功能模块 | 测试用例数 | 覆盖率 |
|---------|-----------|--------|
| **模型层** | 31 | - |
| - ScenarioModel | 18 | 核心功能全覆盖 |
| - TagModel | 13 | 核心功能全覆盖 |
| **辅助层** | 18 | - |
| - TagHelper | 9 | 核心功能全覆盖 |
| - JobHelper | 9 | 核心功能全覆盖 |
| **管理层** | 8 | - |
| - TagManager | 8 | 基础功能覆盖 |
| **总计** | **57** | - |

### 按测试类型分类

| 测试类型 | 测试用例数 | 说明 |
|---------|-----------|------|
| **创建和初始化** | 10 | 测试对象创建和初始化 |
| **配置验证** | 11 | 测试配置有效性验证 |
| **业务逻辑** | 15 | 测试核心业务逻辑 |
| **数据转换** | 5 | 测试序列化/反序列化 |
| **边界条件** | 16 | 测试异常和边界情况 |

---

## 🔍 测试重点

### 1. 配置验证
- ✅ 必需字段验证
- ✅ 字段类型验证
- ✅ INCREMENTAL 模式特殊要求验证
- ✅ 空值和默认值处理

### 2. 更新模式
- ✅ INCREMENTAL 模式
- ✅ REFRESH 模式
- ✅ recompute 标志处理
- ✅ 默认值处理

### 3. 数据加载
- ✅ Settings 文件加载
- ✅ Worker 类加载
- ✅ 错误处理（文件不存在、格式错误等）

### 4. 任务调度
- ✅ Worker 数量决策（根据 job 数量）
- ✅ 日期范围计算（REFRESH/INCREMENTAL 模式）

### 5. 缓存管理
- ✅ Scenario 发现和缓存
- ✅ 缓存刷新
- ✅ 缓存查询

---

## 📝 测试运行说明

### 运行所有测试
```bash
# 使用 pytest
pytest core/modules/tag/__test__/

# 或使用 Python unittest
python -m pytest core/modules/tag/__test__/
```

### 运行特定测试文件
```bash
pytest core/modules/tag/__test__/test_scenario_model.py
```

### 运行特定测试类
```bash
pytest core/modules/tag/__test__/test_scenario_model.py::TestScenarioModel
```

### 运行特定测试方法
```bash
pytest core/modules/tag/__test__/test_scenario_model.py::TestScenarioModel::test_create_from_settings_basic
```

---

## 🔄 更新记录

- **2026-01-17**: 初始版本，包含 57 个测试用例
  - ScenarioModel: 18 个测试用例
  - TagModel: 13 个测试用例
  - TagHelper: 9 个测试用例
  - JobHelper: 9 个测试用例
  - TagManager: 8 个测试用例

---

## 📌 注意事项

1. **Mock 使用**: 大部分测试使用 mock 来隔离外部依赖（DataManager、FileManager 等）
2. **向后兼容**: 测试覆盖了向后兼容的场景（如 target_entity 字符串格式）
3. **边界条件**: 重点关注边界条件和错误处理
4. **配置验证**: 详细测试配置验证逻辑，确保无效配置被正确拒绝
