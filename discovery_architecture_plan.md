# Discovery架构重构计划

## 架构设计原则

### 三层架构

```
Utils层（原子操作）→ Discovery层（批量发现）→ ProjectContext层（便捷代理）
```

**1. Utils层** - 提供原子性的单个操作
- 单个文件查找：`find_file(start_dir, filename)` → Path | None
- 单个文件加载：`load_file_content(file_path)` → str | dict | bytes
- 特点：返回单个对象，无批量处理

**2. Discovery层** - 提供批量发现功能
- 批量文件发现：`discover_files(pattern)` → List[Path]
- 批量目录发现：`discover_directories(pattern)` → List[Path]
- 批量类发现：`discover_classes(config)` → Dict[str, Type]
- 批量模块发现：`discover_objects(pattern)` → Dict[str, Any]
- 特点：返回批量结果（列表/字典），支持动态注册

**3. ProjectContext层** - 提供系统级便捷入口
- 代理discovery的常用操作
- 不照搬所有discovery API
- 只暴露系统真正需要的快捷指令

## 关键设计决策

### Discovery vs Utils的区别

| 维度 | Utils | Discovery |
|------|-------|-----------|
| 操作对象 | 单个文件/对象 | 批量文件/类/模块 |
| 输出类型 | Path/str/dict/None | List/Dict |
| 典型场景 | 查找特定配置文件 | 发现所有handler类 |
| 命名模式 | find_xxx/load_xxx | discover_xxx |

### ProjectContext的角色

**不应该做**：
- ❌ 照搬discovery的所有API
- ❌ 暴露过于底层的文件操作
- ❌ 提供不必要的中间层

**应该做**：
- ✅ 提供系统级的快捷入口（如`get_strategy_directory()`）
- ✅ 代理discovery的高频操作（如`discover_handlers()`）
- ✅ 组合多个discovery调用（如先发现文件，再解析配置）

## Phase 1: 完善Utils层

### 1.1 创建 `core/utils/file.py`

**API设计**：
```python
class FileUtils:
    @staticmethod
    def find_file(
        start_dir: Path,
        filename: str,
        search_parents: bool = False
    ) -> Optional[Path]:
        """
        查找单个文件（向上搜索或向下搜索）

        Args:
            start_dir: 起始目录
            filename: 文件名
            search_parents: 是否向上搜索父目录

        Returns:
            文件路径，未找到返回None
        """
        pass

    @staticmethod
    def load_file_content(
        file_path: Path,
        encoding: str = 'utf-8'
    ) -> Union[str, dict, bytes, None]:
        """
        加载单个文件内容（自动识别JSON/YAML/文本）

        Args:
            file_path: 文件路径
            encoding: 文本编码

        Returns:
            文件内容（字符串/字典/字节），加载失败返回None
        """
        pass

    @staticmethod
    def load_json(file_path: Path) -> Optional[dict]:
        """加载JSON文件"""
        pass

    @staticmethod
    def load_yaml(file_path: Path) -> Optional[dict]:
        """加载YAML文件"""
        pass

    @staticmethod
    def save_file_content(
        file_path: Path,
        content: Union[str, dict, bytes],
        encoding: str = 'utf-8'
    ) -> bool:
        """保存文件内容"""
        pass
```

**职责**：
- 提供原子性的文件操作
- 不涉及批量处理
- 不涉及项目特定的路径逻辑

## Phase 2: 完善Discovery层

### 2.1 创建 `core/infra/discovery/file_discovery.py`

**API设计**：
```python
@dataclass
class FileDiscoveryConfig:
    """文件发现配置"""
    base_dir: Path
    pattern: str = "**/*"  # glob pattern
    exclude_patterns: List[str] = field(default_factory=list)
    file_type: Optional[str] = None  # "file" | "dir" | None (both)


class FileDiscovery:
    """批量文件发现工具"""

    def __init__(self, config: FileDiscoveryConfig):
        self.config = config
        self._cache: Dict[str, List[Path]] = {}

    def discover(self, use_cache: bool = True) -> List[Path]:
        """
        批量发现文件/目录

        Returns:
            文件/目录路径列表
        """
        pass

    def discover_with_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        批量发现文件并提取元数据

        Returns:
            {file_path: {"size": ..., "mtime": ..., "type": ...}}
        """
        pass

    def clear_cache(self):
        """清除缓存"""
        pass


# 便捷函数
def discover_files(
    base_dir: Path,
    pattern: str = "**/*",
    exclude_patterns: List[str] = None
) -> List[Path]:
    """便捷函数：批量发现文件"""
    pass

def discover_directories(
    base_dir: Path,
    pattern: str = "**/*",
    exclude_patterns: List[str] = None
) -> List[Path]:
    """便捷函数：批量发现目录"""
    pass
```

**职责**：
- 批量发现文件/目录
- 返回批量结果（列表/字典）
- 支持缓存机制

### 2.2 保留现有discovery模块

- ✅ `class_discovery.py` - 已经符合批量发现设计
- ✅ `module_discovery.py` - 已经符合批量发现设计

## Phase 3: 精简ProjectContext层

### 3.1 识别保留的API

**保留原则**：
1. 系统级快捷入口（如`get_strategy_directory()`）
2. 高频使用的discovery代理（如`discover_handlers()`）
3. 组合多个discovery调用的便捷方法

**移除原则**：
1. 照搬discovery的API（调用方可直接用discovery）
2. 过于底层的文件操作（应放在utils）
3. 不常用的API（移到底层或删除）

### 3.2 重构后的API示例

```python
class ProjectContext(ProjectContextAPI):
    """项目上下文管理器（精简版）"""

    # ========== 系统级快捷入口 ==========
    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return self._path_manager.project_root

    def get_userspace_root(self) -> Path:
        """获取用户空间根目录"""
        return self._path_manager.userspace_root

    def get_strategy_directory(self, strategy_id: str) -> Path:
        """获取策略目录"""
        return self._path_manager.strategy_directory(strategy_id)

    # ========== Discovery代理（高频） ==========
    def discover_handlers(self) -> Dict[str, Type[BaseHandler]]:
        """发现所有Handler类（代理class_discovery）"""
        return self._discovery_manager.discover_handlers()

    # ========== 不暴露的API ==========
    # 以下API不暴露，调用方直接用底层：
    # - discover_files() → 直接用 FileDiscovery
    # - load_file_content() → 直接用 FileUtils
    # - discover_classes() → 直接用 ClassDiscovery
```

## Phase 4: 迁移调用方

### 4.1 识别所有调用方

```bash
# 查找所有使用ProjectContext的地方
grep -r "ProjectContext\." --include="*.py" | wc -l
```

### 4.2 逐个迁移

**迁移策略**：
1. 底层API（文件操作）→ 迁移到`FileUtils`
2. 批量发现API → 迁移到对应的discovery类
3. 快捷入口API → 保留在`ProjectContext`

## 实施顺序

1. ✅ **Phase 1**: 创建`core/utils/file.py`（单个文件操作）
2. ✅ **Phase 2**: 创建`core/infra/discovery/file_discovery.py`（批量文件发现）
3. ✅ **Phase 3**: 精简`ProjectContext`API（从63个精简到~15个）
4. ✅ **Phase 4**: 迁移调用方（逐步迁移，避免破坏性变更）

## 预期收益

1. **职责清晰**：Utils（原子）、Discovery（批量）、ProjectContext（代理）
2. **API精简**：ProjectContext从63个API精简到~15个
3. **易于测试**：每层职责明确，易于单元测试
4. **易于扩展**：新增发现功能只需扩展Discovery层

## 风险控制

1. **向后兼容**：保留废弃API一段时间，给调用方迁移时间
2. **渐进迁移**：先添加新API，再标记旧API废弃，最后删除
3. **测试覆盖**：每层都有完整的API测试（test_api.py）