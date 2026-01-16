# Project Context 模块单元测试

## 📁 测试组织方式

采用 `__test__` 文件夹方式，测试代码与源代码放在同一目录下：

```
core/infra/project_context/
├── path_manager.py
├── file_manager.py
├── config_manager.py
├── project_context_manager.py
└── __test__/
    ├── __init__.py
    ├── test_path_manager.py
    ├── test_file_manager.py
    ├── test_config_manager.py
    └── test_project_context_manager.py
```

## 🎯 设计理念

- **就近原则**：测试代码与源代码放在一起，便于维护
- **模块化**：每个模块的测试独立，互不干扰
- **清晰命名**：`__test__` 明确表示测试目录

## 🚀 运行测试

### 运行所有测试

```bash
# 在项目根目录
pytest core/infra/project_context/__test__/ -v
```

### 运行特定测试文件

```bash
pytest core/infra/project_context/__test__/test_path_manager.py -v
```

### 运行特定测试类

```bash
pytest core/infra/project_context/__test__/test_path_manager.py::TestPathManager -v
```

### 运行特定测试方法

```bash
pytest core/infra/project_context/__test__/test_path_manager.py::TestPathManager::test_get_root -v
```

## 📋 测试覆盖

### PathManager 测试
- ✅ `get_root()` - 获取项目根目录
- ✅ `core()` - 获取 core 目录
- ✅ `userspace()` - 获取 userspace 目录
- ✅ `config()` - 获取 config 目录
- ✅ `strategy()` - 获取策略目录
- ✅ 根目录缓存机制

### FileManager 测试
- ✅ `find_file()` - 查找文件（递归/非递归）
- ✅ `find_files()` - 查找所有匹配的文件
- ✅ `read_file()` - 读取文件内容
- ✅ `file_exists()` - 检查文件是否存在

### ConfigManager 测试
- ✅ `load_json()` - 加载 JSON 配置文件
- ✅ `get_data_config()` - 获取数据配置
- ✅ `get_default_start_date()` - 获取默认开始日期
- ✅ `get_decimal_places()` - 获取小数位数
- ✅ `get_database_config()` - 获取数据库配置
- ✅ `get_database_type()` - 获取数据库类型
- ✅ `load_with_defaults()` - 加载配置（默认+用户）

### ProjectContextManager 测试
- ✅ `__init__()` - 初始化
- ✅ `core_info()` - 获取 core meta 信息
- ✅ `core_version()` - 获取 core 版本号
- ✅ Facade 模式访问（path、file、config）

## 🔧 测试框架

使用 **pytest** 作为测试框架：

- **优点**：
  - 简洁的语法
  - 丰富的断言
  - 详细的错误信息
  - 支持 fixtures
  - 自动发现测试

## 📝 编写测试的注意事项

1. **测试类命名**：`Test{ClassName}`
2. **测试方法命名**：`test_{method_name}`
3. **使用断言**：`assert` 语句
4. **测试隔离**：每个测试应该独立，不依赖其他测试
5. **测试数据**：使用临时文件或项目中的实际文件

## ✅ 当前状态

- ✅ 27 个测试用例全部通过
- ✅ 覆盖所有主要功能
- ✅ 测试运行时间：< 1 秒
