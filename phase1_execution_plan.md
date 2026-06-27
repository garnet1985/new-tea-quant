# Phase 1: 完成infra/discovery基建 - 详细执行计划

## 一、Phase 1的目标

**目标：完善infra/discovery模块，确保它有足够的底层能力**

当前infra/discovery的能力：
- ClassDiscovery：扫描Python包，发现继承指定基类的子类
- ModuleDiscovery：枚举子包模块中的同名对象（如SCHEMA）
- **缺少的能力：** find_file、load_file_content、find_in_tree

---

## 二、当前infra/discovery的API

| API | 说明 | 是否需要 |
|-----|------|---------|
| ClassDiscovery.discover(base_module_path) | 发现子类 | ✅ 已有 |
| ModuleDiscovery.discover_objects(base_module_path, object_name) | 发现模块对象 | ✅ 已有 |
| **缺失的底层API** | | |

---

## 三、需要添加的底层API

根据ProjectContext的使用情况，infra/discovery需要添加以下底层API：

### 3.1 find_file（底层文件发现）

```python
from core.infra.discovery import FileDiscovery

# 用法：
file_path = FileDiscovery.find_file(
    filename="settings.py",
    search_dir=Path("userspace/strategies"),
    recursive=True
)
```

**说明：**
- 在指定目录下查找文件
- 支持递归查找
- 返回第一个找到的文件路径

---

### 3.2 load_file_content（底层文件加载）

```python
from core.infra.discovery import FileDiscovery

# 用法：
content = FileDiscovery.load_file_content(
    path=Path("settings.py"),
    encoding="utf-8"
)
```

**说明：**
- 加载文件内容
- 支持指定编码
- 返回字符串，失败返回None

---

### 3.3 find_in_tree（底层目录树发现）

```python
from core.infra.discovery import FileDiscovery

# 用法：
file_path = FileDiscovery.find_in_tree(
    base_dir=Path("core/modules/data_source/handlers"),
    key="mongodb",
    config_filename="config.py"
)
```

**说明：**
- 在目录树中查找配置文件
- 支持多种查找模式（直接路径、递归查找）
- 返回找到的文件路径

---

## 四、实现方式

**方案A：创建FileDiscovery类（推荐）**

```python
# core/infra/discovery/file_discovery.py

class FileDiscovery:
    """底层文件发现与加载工具"""
    
    @staticmethod
    def find_file(filename: str, search_dir: Path, recursive: bool = True) -> Optional[Path]:
        """在指定目录下查找文件"""
        pass
    
    @staticmethod
    def load_file_content(path: Path, encoding: str = "utf-8") -> Optional[str]:
        """加载文件内容"""
        pass
    
    @staticmethod
    def find_in_tree(base_dir: Path, key: str, config_filename: str = "config.py") -> Optional[Path]:
        """在目录树中查找配置文件"""
        pass
```

---

**方案B：直接添加到现有的ModuleDiscovery类**

```python
# core/infra/discovery/module_discovery.py

class ModuleDiscovery:
    """模块发现与文件操作"""
    
    # 现有方法
    def discover_objects(...): ...
    
    # 新增方法
    @staticmethod
    def find_file(...): ...
    
    @staticmethod
    def load_file_content(...): ...
    
    @staticmethod
    def find_in_tree(...): ...
```

---

## 五、我的推荐

**推荐方案A：创建FileDiscovery类**

理由：
1. **职责清晰**：ClassDiscovery负责类发现，ModuleDiscovery负责模块发现，FileDiscovery负责文件发现
2. **符合单一职责**：每个类只负责一种发现能力
3. **便于扩展**：未来如果有新的文件发现需求，直接在FileDiscovery中添加
4. **便于使用**：用户可以按需import不同的Discovery类

---

## 六、Phase 1的执行步骤

**Step 1：创建FileDiscovery类**
- 创建 `core/infra/discovery/file_discovery.py`
- 实现 `find_file`、`load_file_content`、`find_in_tree` 三个方法
- 从 `core/infra/project_context/file_manager.py` 中复制现有实现（已有这些方法）

**Step 2：更新infra/discovery的__init__.py**
- 在 `__init__.py` 中导出 `FileDiscovery`
- 确保用户可以通过 `from core.infra.discovery import FileDiscovery` 使用

**Step 3：更新infra/discovery的API文档**
- 更新 `docs/API.md`
- 更新 `module_info.yaml`

**Step 4：添加测试**
- 创建 `__test__/test_file_discovery.py`
- 添加单元测试

**Step 5：验证**
- 运行测试验证
- 确保所有方法都能正常工作

---

## 七、需要确认

请确认以下几点：

1. **是否同意创建FileDiscovery类？** 还是直接添加到现有的ModuleDiscovery类？
2. **这三个方法是否足够？** find_file、load_file_content、find_in_tree？
3. **是否需要其他底层文件发现能力？**
4. **是否同意这个执行顺序？** 先完成FileDiscovery，再更新文档和测试？

确认后我就开始执行Phase 1。