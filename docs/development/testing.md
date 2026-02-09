# 测试指南

## 测试框架

项目使用 `pytest` 作为测试框架。

## 运行测试

### 运行所有测试

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行所有测试
pytest $(find core -type d -name "__test__" | tr '\n' ' ') -v
```

### 运行特定模块测试

```bash
# 运行数据库模块测试
pytest core/infra/db/__test__/ -v

# 运行策略模块测试
pytest core/modules/strategy/__test__/ -v
```

### 运行特定测试文件

```bash
pytest core/infra/db/__test__/test_db_manager.py -v
```

### 运行特定测试方法

```bash
pytest core/infra/db/__test__/test_db_manager.py::TestDatabaseManager::test_init -v
```

## 测试覆盖率

### 生成覆盖率报告

```bash
# 生成终端报告
pytest --cov=core --cov-report=term --cov-config=.coveragerc $(find core -type d -name "__test__" | tr '\n' ' ')

# 生成 HTML 报告
pytest --cov=core --cov-report=html --cov-config=.coveragerc $(find core -type d -name "__test__" | tr '\n' ' ')
open htmlcov/index.html
```

### 覆盖率配置

配置文件：`.coveragerc`

- 排除 `userspace/` 目录（用户代码）
- 排除 `__test__/` 目录（测试代码）
- 排除示例文件

详细说明：[覆盖率配置](coverage.md)

## 测试组织

### 目录结构

测试文件放在各模块的 `__test__/` 目录下：

```
core/modules/strategy/
├── components/
└── __test__/
    ├── test_opportunity_enumerator.py
    └── README.md
```

### 测试文件命名

- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试方法：`test_*`

## 编写测试

### 基本测试示例

```python
import pytest
from core.infra.db import DatabaseManager

class TestDatabaseManager:
    def test_init(self):
        """测试初始化"""
        db = DatabaseManager()
        assert db is not None
```

### Mock 使用

```python
from unittest.mock import Mock, patch

@patch('core.infra.db.DatabaseManager.get_default')
def test_with_mock(mock_get_default):
    mock_get_default.return_value = Mock()
    # 测试代码
```

## 测试文档

各模块的测试文档位于 `__test__/README.md`：

- [数据库测试文档](../../core/infra/db/__test__/README.md)
- [策略测试文档](../../core/modules/strategy/__test__/README.md)
- [Worker 测试文档](../../core/infra/worker/__test__/README.md)

## 相关文档

- [覆盖率配置](coverage.md)
- [代码规范](code-style.md)
- [贡献指南](contributing.md)
