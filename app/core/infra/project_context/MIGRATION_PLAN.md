# Project Management Module - 迁移计划

本文档包含从现有代码迁移到 Project Management Module 的详细计划和待办事项。

## 📋 迁移目标

1. 替换所有硬编码路径为 `PathManager` 方法
2. 替换所有 `FileUtil` 调用为 `FileManager`
3. 统一配置加载使用 `ConfigManager.load_with_defaults`
4. 支持从 `app/` 目录结构迁移到根目录结构（`core/`、`userspace/`）

## ✅ 阶段 1：创建模块（不破坏现有代码）

- [x] 创建 `core/infra/path/` 目录结构
- [x] 实现 `PathManager`（项目根目录检测和路径方法）
- [x] 实现 `FileManager`（文件查找、读取等操作）
- [x] 实现 `ConfigManager`（配置加载和合并）
- [x] 实现 `ProjectContextManager`（Facade）
- [ ] 编写单元测试
- [x] 更新 `__init__.py` 导出

**状态**：✅ **基本完成**（单元测试待后续补充）

## ✅ 阶段 2：逐步替换硬编码路径

**状态**：✅ **已完成**

### 2.1 替换策略相关路径

- [x] 查找所有 `app/userspace/strategies/...` 硬编码路径
- [x] 替换为 `PathManager.strategy(...)` 或 `PathManager.strategy_settings(...)`
- [x] 替换 `app/core/modules/strategy/...` → `PathManager.core() / "modules" / "strategy" / ...`
- [x] 测试策略发现功能
- [x] 测试策略配置加载

**涉及文件**：
- `app/core/modules/strategy/helper/strategy_discovery_helper.py`
- `app/core/modules/strategy/components/opportunity_service.py`
- `app/core/modules/strategy/components/session_manager.py`
- `app/core/modules/strategy/managers/version_manager.py`
- `app/core/modules/strategy/managers/result_path_manager.py`

### 2.2 替换标签相关路径

- [x] 查找所有 `app/userspace/tags/...` 硬编码路径
- [x] 替换为 `PathManager.tag_scenario(...)` 或 `get_scenarios_root()`
- [x] 测试标签发现功能

**涉及文件**：
- `app/core/modules/tag/core/config.py`
- `app/core/modules/tag/core/tag_manager.py`

### 2.3 替换数据源相关路径

- [x] 查找所有数据源配置路径硬编码
- [x] 替换为 `PathManager` 方法
- [x] 测试数据源配置加载

**涉及文件**：
- `app/core/modules/data_source/data_source_manager.py`

### 2.4 替换 FileUtil 调用

- [x] 查找所有 `FileUtil` 的调用
- [x] 替换为 `FileManager` 对应方法
- [x] 测试文件查找功能
- [x] 测试文件读取功能

**涉及文件**：
- `app/core/modules/tag/core/components/helper/tag_helper.py` ✅
- `app/core/modules/data_manager/data_manager.py` ✅

**剩余文件**（仅导出，不影响功能）：
- `app/core/utils/file/__init__.py` - 仅导出，待后续删除

## ✅ 阶段 3：统一配置加载

**状态**：✅ **基本完成**

- [x] 查找所有手动加载和合并配置的代码
- [x] 替换为 `ConfigManager.load_with_defaults` 或 `ConfigManager.load_json`
- [x] 测试配置合并逻辑
- [x] 验证深度合并和完全覆盖功能

**涉及文件**：
- `app/core/modules/data_source/data_source_manager.py`（`_load_mapping` 方法）✅
  - 已使用 `ConfigManager.load_json` 加载配置
  - 已使用 `merge_mapping_configs` 进行深度合并
  - 保留了兼容旧路径的逻辑

**其他文件说明**：
- `app/core/conf/db_conf.py` - 数据库配置加载，包含复杂的格式转换逻辑，暂不替换
- `app/core/infra/db/db_config_manager.py` - 数据库配置管理器，暂不替换
- 其他 JSON 加载多为数据文件（非配置文件），不在替换范围内

## ✅ 阶段 4：目录结构迁移

### 4.1 准备迁移脚本

- [ ] 创建迁移脚本（移动 `app/core` → `core`）
- [ ] 创建迁移脚本（移动 `app/userspace` → `userspace`）
- [ ] 创建导入语句更新脚本
- [ ] 测试迁移脚本（在测试分支）

### 4.2 执行迁移

- [ ] 备份当前代码
- [ ] 移动 `app/core` → `core`
- [ ] 移动 `app/userspace` → `userspace`
- [ ] 更新所有导入语句（`from app.core` → `from core`）
- [ ] 更新 `PathManager` 适配新路径结构
- [ ] 运行所有测试

### 4.3 验证迁移

- [ ] 验证策略发现功能
- [ ] 验证策略配置加载
- [ ] 验证标签功能
- [ ] 验证数据源功能
- [ ] 验证文件查找功能
- [ ] 验证配置合并功能

## ✅ 阶段 5：清理和优化

### 5.1 删除废弃代码

- [ ] 确认所有 `FileUtil` 调用已替换
- [ ] 删除 `app/core/utils/file/file_util.py`（FileUtil）
- [ ] 删除 `app/` 目录（如果已完全迁移）
- [ ] 更新 `.gitignore`

### 5.2 更新文档

- [ ] 更新 README.md（路径说明）
- [ ] 更新所有涉及路径的文档
- [ ] 更新代码示例

### 5.3 代码审查

- [ ] 全局搜索硬编码路径，确保都已替换
- [ ] 全局搜索 `FileUtil`，确保都已替换
- [ ] 代码审查和优化

## 📊 进度跟踪

### 当前阶段
- [ ] 阶段 1：创建模块
- [ ] 阶段 2：逐步替换硬编码路径
- [ ] 阶段 3：统一配置加载
- [ ] 阶段 4：目录结构迁移
- [ ] 阶段 5：清理和优化

### 统计信息

- **硬编码路径数量**：待统计
- **FileUtil 调用数量**：待统计
- **配置加载位置数量**：待统计

## 🔍 查找工具

### 查找硬编码路径

```bash
# 查找 app/userspace 硬编码
grep -r "app/userspace" app/ --include="*.py"

# 查找 app/core 硬编码
grep -r "app/core" app/ --include="*.py"

# 查找 Path 硬编码（字符串）
grep -r 'Path("app/' app/ --include="*.py"
grep -r "Path('app/" app/ --include="*.py"
```

### 查找 FileUtil 调用

```bash
# 查找 FileUtil 导入
grep -r "from.*FileUtil" app/ --include="*.py"
grep -r "import.*FileUtil" app/ --include="*.py"

# 查找 FileUtil 使用
grep -r "FileUtil\." app/ --include="*.py"
```

### 查找配置加载代码

```bash
# 查找 json.load
grep -r "json.load" app/ --include="*.py"

# 查找 importlib.import_module（配置加载）
grep -r "importlib.import_module.*settings" app/ --include="*.py"
```

## 📝 注意事项

1. **备份**：迁移前务必备份代码
2. **测试**：每个阶段完成后运行完整测试
3. **渐进式**：不要一次性替换所有代码，分阶段进行
4. **验证**：每个替换后都要验证功能正常
5. **文档**：及时更新相关文档

## 🎯 成功标准

- [ ] 所有硬编码路径替换为 `PathManager` 方法
- [ ] 所有 `FileUtil` 调用替换为 `FileManager`
- [ ] 所有配置加载使用 `ConfigManager.load_with_defaults`
- [ ] 支持从 `app/` 目录结构迁移到根目录结构
- [ ] `FileUtil` 被完全淘汰并删除
- [ ] 代码库中不再有 `app/` 路径的硬编码
- [ ] 所有测试通过
