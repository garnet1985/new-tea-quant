# Discovery 模块单元测试

## 📋 概述

本目录包含 `discovery` 模块的单元测试。

## 🧪 测试文件

- `test_class_discovery.py` - ClassDiscovery 测试
- `test_module_discovery.py` - ModuleDiscovery 测试

## 🚀 运行测试

### 使用 pytest（推荐）

```bash
# 运行所有测试
pytest core/infra/discovery/__test__/

# 运行特定测试文件
pytest core/infra/discovery/__test__/test_class_discovery.py
```

### 直接运行（无需 pytest）

```bash
# 运行单个测试文件
python core/infra/discovery/__test__/test_class_discovery.py
```

## 📝 测试覆盖

### ClassDiscovery
- ✅ 通过路径发现类
- ✅ 发现类的属性（config_class）
- ✅ 使用配置发现类
- ✅ 缓存机制

### ModuleDiscovery
- ✅ 发现模块对象（SCHEMA）
- ✅ 通过路径发现模块

## 🔧 添加新测试

1. 在对应的测试文件中添加测试方法
2. 测试方法名以 `test_` 开头
3. 使用 `assert` 进行断言
4. 如果测试需要 mock，使用 `unittest.mock`
