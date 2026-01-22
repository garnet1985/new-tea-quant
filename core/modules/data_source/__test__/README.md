# Data Source 模块单元测试

## 📋 概述

本目录包含 `data_source` 模块的单元测试。

## 🧪 测试文件

- `test_data_source_manager.py` - DataSourceManager 测试
- `test_data_source_handler.py` - BaseDataSourceHandler 测试
- `test_api_job.py` - ApiJob 测试
- `test_definition.py` - DataSourceDefinition 测试

## 🚀 运行测试

### 使用 pytest（推荐）

```bash
# 运行所有测试
pytest core/modules/data_source/__test__/

# 运行特定测试文件
pytest core/modules/data_source/__test__/test_data_source_manager.py

# 运行特定测试方法
pytest core/modules/data_source/__test__/test_data_source_manager.py::TestDataSourceManager::test_init
```

### 直接运行（无需 pytest）

```bash
# 运行单个测试文件
python core/modules/data_source/__test__/test_data_source_manager.py
```

## 📝 测试覆盖

### DataSourceManager
- ✅ 初始化
- ✅ Handler 路径验证
- ✅ 获取 DataSourceDefinition
- ✅ 列出数据源
- ✅ 获取 Handler 状态

### BaseDataSourceHandler
- ✅ 初始化验证（必须提供 definition）
- ✅ 类属性验证（必须定义 data_source）
- ✅ 获取配置参数
- ✅ 获取 ProviderConfig 和 HandlerConfig
- ✅ 创建简单 Task

### ApiJob
- ✅ ApiJob 初始化
- ✅ api_name 自动设置
- ✅ 依赖关系

注意：DataSourceTask 已被 ApiJobBatch 取代，相关测试已移除。

### DataSourceDefinition
- ✅ 从字典创建
- ✅ 验证方法
- ✅ 序列化为字典

## 🔧 添加新测试

1. 在对应的测试文件中添加测试方法
2. 测试方法名以 `test_` 开头
3. 使用 `assert` 进行断言
4. 如果测试需要 mock，使用 `unittest.mock`
