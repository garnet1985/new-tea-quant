# Utils 模块单元测试

## 📁 测试文件结构

```
core/utils/__test__/
├── __init__.py
├── test_util.py              # 配置合并工具测试
├── test_date_utils.py        # 日期工具类测试
└── test_icon_service.py      # 图标服务测试
```

## 🚀 运行测试

### 使用 pytest（推荐）

```bash
# 运行所有测试
pytest core/utils/__test__/ -v

# 运行特定测试文件
pytest core/utils/__test__/test_date_utils.py -v

# 运行特定测试类
pytest core/utils/__test__/test_date_utils.py::TestDateUtils -v

# 运行特定测试方法
pytest core/utils/__test__/test_date_utils.py::TestDateUtils::test_get_next_date -v
```

### 使用 Python 直接运行

```bash
# 运行单个测试文件
python3 -m pytest core/utils/__test__/test_util.py -v
```

## 📝 测试覆盖

### test_util.py
- ✅ `deep_merge_config` - 深度合并配置
- ✅ `merge_mapping_configs` - 合并 mapping 配置

### test_date_utils.py
- ✅ 日期格式转换
- ✅ 日期计算（前后 N 天）
- ✅ 日期范围生成
- ✅ 季度转换
- ✅ 日期标准化
- ✅ 日期比较

### test_icon_service.py
- ✅ 图标获取（各种类型）
- ✅ 大小写不敏感
- ✅ 简化 API `i()`

## 📊 测试统计

- **测试文件**: 3 个
- **测试类**: 5 个
- **测试方法**: 41 个

## 🔍 测试示例

### 日期工具测试

```python
from core.utils.date.date_utils import DateUtils

# 测试日期转换
assert DateUtils.get_next_date("20240115") == "20240116"
assert DateUtils.get_previous_day("20240115") == "20240114"

# 测试季度转换
assert DateUtils.date_to_quarter("20240115") == "2024Q1"
assert DateUtils.quarter_to_date("2024Q1", is_start=True) == "20240101"
```

### 图标服务测试

```python
from core.utils import i

# 测试简化 API
assert i("success") == "✅"
assert i("green_dot") == "🟢"
```

### 配置合并测试

```python
from core.utils.util import deep_merge_config

defaults = {"params": {"a": 1, "b": 2}}
custom = {"params": {"b": 3, "c": 4}}
result = deep_merge_config(defaults, custom, deep_merge_fields={"params"})
assert result["params"] == {"a": 1, "b": 3, "c": 4}
```
