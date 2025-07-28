# Python 文件命名规范指南

## 问题：`xxx.xxx.py` 命名方式是否支持？

**答案：不支持！** Python 不支持文件名中包含点号（除了扩展名）。

## 1. Python 文件命名规则

### ❌ 不允许的命名方式：
```python
# 这些都会导致导入问题
app.data_source.providers.tushare.main.py  # ❌ 包含点号
my-module.py                               # ❌ 包含连字符
my module.py                               # ❌ 包含空格
123module.py                               # ❌ 以数字开头
main.service.py                            # ❌ 包含点号
main.storage.py                            # ❌ 包含点号
```

### ✅ 推荐的命名方式：
```python
# 这些是正确的命名
main.py                                    # ✅ 简单名称
tushare_main.py                           # ✅ 下划线分隔
data_source_provider.py                   # ✅ 下划线分隔
main_v2.py                                # ✅ 版本号
tushare_service.py                        # ✅ 描述性名称
tushare_storage.py                        # ✅ 描述性名称
```

## 2. 为什么 `xxx.xxx.py` 会导致问题？

### 2.1 Python 模块系统的工作原理
```python
# 当你有一个文件 main.service.py 时
# Python 会尝试这样解析：
main.service  # 被解释为 main 模块下的 service 子模块
# 但 main.py 不是一个包，所以无法包含子模块
```

### 2.2 实际错误示例
```python
# 尝试导入 main.service.py
from app.data_source.providers.tushare.main.service import TushareService
# 错误：ModuleNotFoundError: No module named 'app.data_source.providers.tushare.main.service'
```

## 3. 正确的项目结构

### 3.1 使用下划线分隔
```
app/
├── data_source/
│   └── providers/
│       └── tushare/
│           ├── main.py
│           ├── tushare_service.py      # ✅ 正确
│           ├── tushare_storage.py      # ✅ 正确
│           └── settings.py
```

### 3.2 使用包结构（如果需要）
```
app/
├── data_source/
│   └── providers/
│       └── tushare/
│           ├── main/
│           │   ├── __init__.py
│           │   ├── service.py          # ✅ 作为包的子模块
│           │   └── storage.py          # ✅ 作为包的子模块
│           └── settings.py
```

## 4. 导入语句的对应关系

### 4.1 文件重命名前（错误）
```python
# 文件：main.service.py, main.storage.py
from app.data_source.providers.tushare.main.service import TushareService  # ❌ 失败
from app.data_source.providers.tushare.main.storage import TushareStorage  # ❌ 失败
```

### 4.2 文件重命名后（正确）
```python
# 文件：tushare_service.py, tushare_storage.py
from app.data_source.providers.tushare.tushare_service import TushareService  # ✅ 成功
from app.data_source.providers.tushare.tushare_storage import TushareStorage  # ✅ 成功
```

## 5. 最佳实践建议

### 5.1 文件命名原则
1. **使用下划线分隔单词**：`tushare_service.py`
2. **使用小写字母**：`main.py` 而不是 `Main.py`
3. **避免特殊字符**：只使用字母、数字、下划线
4. **使用描述性名称**：`data_processor.py` 而不是 `dp.py`

### 5.2 模块组织原则
1. **单一职责**：每个文件只负责一个功能
2. **清晰的层次结构**：使用目录组织相关模块
3. **避免过深的嵌套**：不要超过4-5层目录

### 5.3 导入语句原则
1. **使用绝对导入**：`from app.module import Class`
2. **避免相对导入**：`from .module import Class`（除非在包内）
3. **明确导入**：`from module import specific_class`

## 6. 常见错误和解决方案

### 6.1 错误：文件名包含点号
```python
# 错误文件：main.service.py
# 解决方案：重命名为 main_service.py 或 tushare_service.py
```

### 6.2 错误：文件名包含连字符
```python
# 错误文件：my-module.py
# 解决方案：重命名为 my_module.py
```

### 6.3 错误：文件名包含空格
```python
# 错误文件：my module.py
# 解决方案：重命名为 my_module.py
```

## 7. 工具和检查

### 7.1 检查项目中的问题文件
```bash
# 查找包含点号的文件（除了 .py 扩展名）
find . -name "*.py" | grep -E "\." | grep -v "\.py$"

# 查找包含连字符的文件
find . -name "*.py" | grep "-"
```

### 7.2 批量重命名示例
```bash
# 重命名包含点号的文件
mv main.service.py tushare_service.py
mv main.storage.py tushare_storage.py
```

## 8. 总结

- **❌ 不要使用**：`xxx.xxx.py`、`xxx-xxx.py`、`xxx xxx.py`
- **✅ 推荐使用**：`xxx_xxx.py`、`xxx.py`
- **导入时**：使用下划线分隔的模块名
- **组织时**：使用目录结构而不是文件名来组织代码

遵循这些规范可以避免导入错误，让代码更加清晰和可维护！ 