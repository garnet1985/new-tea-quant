# Tag 系统执行流程设计

本文档描述 Tag 系统的完整执行流程。

---

## 整体流程

```
1. 用户创建 TagManager 并调用 run()
2. TagManager 自动检查所有 scenarios，读取类和 settings
3. Validation 后，每个 enable 的 calculator 缓存在 manager 里
4. 循环执行每个 calculator 的入口函数（scenario 之间同步操作）
5. 每个 calculator 的入口函数：
   a. 检查 DB 是否创建了 scenario 和 tags（create 流程）
   b. 如果已创建，进入 renew 流程
6. Renew 流程：
   a. 对比 version
   b. 如果 version 不同，进入 on_version_change 流程
   c. 如果 version 相同，按 update_mode 计算
7. Version 变化处理：
   a. NEW_SCENARIO: 创建新 scenario，标记老 tags 为 legacy，清理旧版本
   b. REFRESH_SCENARIO: 删除之前结果，重新计算
```

---

## 详细流程设计

### 阶段 1: TagManager 初始化

```python
tag_manager = TagManager(data_mgr=data_manager)
```

**执行内容**：
1. 从配置读取 scenarios 根目录
2. 初始化 TagService
3. 调用 `_load_and_register_scenarios()`

### 阶段 2: 发现和注册 Scenarios

```python
def _load_and_register_scenarios(self):
    """
    发现所有 scenario calculators 并自动注册到数据库
    """
    # 遍历 scenarios 目录
    # 对每个 scenario：
    #   1. 检查 calculator.py 和 settings.py 存在性
    #   2. 加载 settings 和 calculator 类
    #   3. 验证 settings 基本结构
    #   4. 存储到缓存
    #   5. **不在这里注册到数据库**（延迟到 run() 时）
```

**设计决策**：
- **不在初始化时注册**：避免初始化时做数据库操作，延迟到 `run()` 时统一处理
- **只做发现和验证**：确保所有 scenarios 都是有效的

### 阶段 3: 执行入口

```python
def run(self, data_source_mgr=None):
    """
    执行所有 scenarios 的计算
    
    Args:
        data_source_mgr: DataSourceManager 实例（可选）
    """
    # 1. 对每个 enable 的 scenario（同步执行）：
    #    a. 获取 calculator 实例（自动创建并缓存）
    #    b. 调用 calculator.run()
    # 2. 等待所有 scenarios 完成
```

### 阶段 4: Calculator 执行流程

```python
class BaseTagCalculator:
    def run(self, data_source_mgr=None):
        """
        Calculator 入口函数
        
        流程：
        1. 检查 DB 是否创建了 scenario 和 tags（create 流程）
        2. 如果已创建，进入 renew 流程
        """
        # 1. 获取 scenario 信息（从 settings）
        #    scenario_name = self.scenario_name
        #    version = self.scenario_version
        
        # 2. 检查 scenario 是否已存在（通过 TagService）
        #    existing_scenario = self.tag_service.get_scenario(scenario_name, version)
        
        # 3. 如果不存在：
        #    - 进入 create 流程
        # 4. 如果已存在：
        #    - 进入 renew 流程
        pass
    
    def _create_scenario_and_tags(self):
        """
        Create 流程：创建 scenario 和 tag definitions
        """
        # 1. 创建 scenario（通过 TagService）
        #    scenario_id = self.tag_service.create_scenario(...)
        # 
        # 2. 创建 tag definitions（遍历 settings.tags）
        #    for tag in self.tags_config:
        #        tag_definition_id = self.tag_service.create_tag_definition(...)
        # 
        # 3. 进入计算流程（首次计算）
        #    self._calculate_tags()
        pass
    
    def _renew_scenario(self):
        """
        Renew 流程：更新 scenario 和计算 tags
        """
        # 1. 获取当前 scenario 信息
        #    current_scenario = self.tag_service.get_scenario(self.scenario_name, self.scenario_version)
        # 
        # 2. 对比 version
        #    db_version = current_scenario["version"]
        #    config_version = self.scenario_version
        # 
        # 3. 如果 version 相同：
        #    - 按 update_mode 计算（调用 _calculate_tags）
        # 
        # 4. 如果 version 不同：
        #    - 进入 on_version_change 流程
        pass
    
    def _handle_version_change(self, existing_scenario: Dict[str, Any]):
        """
        处理版本变更
        
        Args:
            existing_scenario: 数据库中已存在的 scenario 信息
        """
        # 1. 读取 on_version_change 配置
        #    on_version_change = self.settings["scenario"].get("on_version_change", "REFRESH_SCENARIO")
        # 
        # 2. 如果是 NEW_SCENARIO：
        #    - 调用 _handle_new_scenario()
        # 
        # 3. 如果是 REFRESH_SCENARIO：
        #    - 调用 _handle_refresh_scenario()
        pass
    
    def _handle_new_scenario(self, existing_scenario: Dict[str, Any]):
        """
        处理 NEW_SCENARIO：创建新 scenario，保留旧的
        """
        # 1. 创建新的 scenario（通过 TagService）
        #    new_scenario_id = self.tag_service.create_scenario(
        #        name=self.scenario_name,
        #        version=self.scenario_version,
        #        ...
        #    )
        # 
        # 2. 创建新的 tag definitions
        #    for tag in self.tags_config:
        #        tag_definition_id = self.tag_service.create_tag_definition(
        #            scenario_id=new_scenario_id,
        #            ...
        #        )
        # 
        # 3. 标记旧的 scenario 和 tags 为 legacy
        #    old_scenario_id = existing_scenario["id"]
        #    self.tag_service.mark_scenario_as_legacy(old_scenario_id)
        #    # TagService 自动标记该 scenario 下的所有 tag definitions 为 legacy
        # 
        # 4. 清理旧版本（如果 legacy version >= 3，删除最老的）
        #    self.tag_service.cleanup_old_versions(self.scenario_name, max_versions=3)
        # 
        # 5. 进入计算流程（计算新 scenario 的 tags）
        #    self._calculate_tags(new_scenario_id)
        pass
    
    def _handle_refresh_scenario(self, existing_scenario: Dict[str, Any]):
        """
        处理 REFRESH_SCENARIO：删除之前结果，重新计算
        """
        # 1. 更新 scenario 记录（通过 TagService）
        #    scenario_id = existing_scenario["id"]
        #    self.tag_service.update_scenario(scenario_id, ...)
        # 
        # 2. 删除旧的 tag definitions
        #    self.tag_service.delete_tag_definitions_by_scenario(scenario_id)
        # 
        # 3. 创建新的 tag definitions
        #    for tag in self.tags_config:
        #        tag_definition_id = self.tag_service.create_tag_definition(...)
        # 
        # 4. 删除旧的 tag values（可选，或者让计算时覆盖）
        #    # 可以通过删除 tag_value 表中对应的记录，或者让计算时自动覆盖
        # 
        # 5. 进入计算流程（重新计算所有 tags）
        #    self._calculate_tags(scenario_id)
        pass
    
    def _calculate_tags(self, scenario_id: int):
        """
        计算 tags（根据 update_mode）
        """
        # 1. 获取 scenario 的 tag definitions
        #    tag_definitions = self.tag_service.get_tag_definitions(scenario_id=scenario_id)
        # 
        # 2. 确定计算日期范围（根据 update_mode）
        #    - INCREMENTAL: 从上次计算的最大 as_of_date 继续
        #    - REFRESH: 从 start_date 到 end_date
        # 
        # 3. 获取实体列表（如股票列表）
        # 
        # 4. 对每个实体：
        #    a. 加载历史数据（调用 self.load_entity_data）
        #    b. 对每个 tag：
        #        * 调用 self.calculate_tag()
        #        * 如果返回结果，保存 tag 值（调用 self.save_tag_value）
        # 
        # 5. 调用 self.on_finish()
        pass
```

---

## 关键设计决策

### 1. 注册时机：延迟到 run() 时

**问题**：Scenario 和 Tag Definition 的注册应该在什么时候完成？

**方案 A**：在 TagManager 初始化时注册（之前的设计）
- 优点：初始化时就完成所有注册
- 缺点：初始化时做数据库操作，可能影响性能

**方案 B**：延迟到 calculator.run() 时注册（当前流程）
- 优点：按需注册，只在真正需要计算时才注册
- 缺点：需要每个 calculator 都检查并注册

**推荐**：采用方案 B，但可以优化：
- TagManager 在发现时只做验证和缓存
- Calculator.run() 时检查并注册（create 流程）
- 这样更灵活，支持动态添加 scenario

### 2. Version 对比时机：在 Calculator.run() 时

**流程**：
1. Calculator.run() 时检查 scenario 是否存在
2. 如果存在，对比 version
3. 根据 version 是否相同决定流程

**优点**：
- 每次执行时都检查 version，确保一致性
- 支持动态修改 settings 中的 version

### 3. Legacy Version 清理：在 TagService 中实现

**逻辑**：
- 当创建新 scenario 时，如果该 scenario 的 legacy version >= 3，删除最老的
- 配置项：`MAX_LEGACY_VERSIONS = 3`（可配置）

**实现位置**：TagService.cleanup_old_versions()

### 4. 同步 vs 异步执行

**当前设计**：Scenario 之间同步执行

**考虑**：
- 同步执行：简单，易于调试，避免资源竞争
- 异步执行：性能更好，但需要处理并发和资源管理

**推荐**：先实现同步，后续可以支持异步（通过配置）

---

## 流程优化建议

### 建议 1: 分离 Create 和 Renew 流程

**当前流程**：Calculator.run() 中检查并决定进入 create 或 renew

**优化**：可以更清晰地分离：
```python
def run(self):
    if self._scenario_exists():
        self._renew_scenario()
    else:
        self._create_scenario_and_tags()
```

### 建议 2: Version 对比逻辑

**当前流程**：在 renew 流程中对比 version

**优化**：可以提取为独立方法：
```python
def _check_version_change(self, existing_scenario):
    """
    检查版本是否变化
    
    Returns:
        Tuple[bool, str]: (是否变化, 变化类型: "same" | "changed")
    """
    db_version = existing_scenario["version"]
    config_version = self.scenario_version
    if db_version == config_version:
        return False, "same"
    else:
        return True, "changed"
```

### 建议 3: Legacy Version 清理策略

**当前设计**：创建新 scenario 时清理

**优化**：可以在 TagService 中实现自动清理：
```python
def cleanup_old_versions(self, scenario_name: str, max_versions: int = 3):
    """
    清理旧的 legacy versions
    
    如果 legacy version 数量 >= max_versions，删除最老的
    """
    # 1. 查询所有 legacy scenarios（按 created_at 排序）
    # 2. 如果数量 >= max_versions：
    #    - 删除最老的 scenario 及其 tag definitions 和 tag values
    # 3. 返回清理结果
```

### 建议 4: 错误处理

**当前流程**：没有明确的错误处理策略

**建议**：
- 每个 scenario 的计算错误不应该影响其他 scenarios
- 使用 try-except 包裹每个 scenario 的执行
- 记录错误日志，继续执行其他 scenarios

---

## 完整流程伪代码

```python
# ========================================================================
# 1. 初始化 TagManager
# ========================================================================
tag_manager = TagManager(data_mgr=data_manager)

# TagManager 自动完成：
# - 发现所有 scenarios
# - 加载 settings 和 calculator 类
# - 验证配置
# - 缓存 enable 的 calculators

# ========================================================================
# 2. 执行所有 Scenarios
# ========================================================================
tag_manager.run(data_source_mgr=data_source_manager)

# TagManager.run() 流程：
# 对每个 enable 的 scenario（同步执行）：
#   1. 获取 calculator 实例（自动创建并缓存）
#   2. 调用 calculator.run()
#   3. 等待完成

# Calculator.run() 流程：
#   1. 检查 scenario 是否存在
#   2. 如果不存在：
#      - 创建 scenario 和 tag definitions（create 流程）
#      - 进入计算流程
#   3. 如果已存在：
#      - 对比 version
#      - 如果 version 相同：
#          * 按 update_mode 计算（renew 流程）
#      - 如果 version 不同：
#          * 根据 on_version_change 处理：
#            - NEW_SCENARIO: 创建新 scenario，标记旧的为 legacy，清理旧版本
#            - REFRESH_SCENARIO: 删除旧 tags，重新计算
#          * 进入计算流程

# 计算流程：
#   1. 确定计算日期范围（根据 update_mode）
#   2. 获取实体列表
#   3. 对每个实体：
#      a. 加载历史数据
#      b. 对每个 tag：
#          * 调用 calculate_tag()
#          * 保存 tag 值
#   4. 调用 on_finish()
```

---

## 潜在问题和建议

### 问题 1: Create 流程的位置

**当前设计**：在 Calculator.run() 中检查并创建

**问题**：如果多个地方调用 calculator，可能会重复检查

**建议**：可以在 TagManager 的 `_load_and_register_scenarios()` 中就完成注册，但只注册元信息，不执行计算。这样更清晰。

### 问题 2: Version 对比的时机

**当前设计**：在 Calculator.run() 时对比

**问题**：如果 settings 中的 version 在运行过程中被修改，可能会有不一致

**建议**：在 Calculator.run() 时对比是合理的，因为：
- 每次执行时都检查，确保一致性
- 支持动态修改 version

### 问题 3: Legacy Version 清理

**当前设计**：创建新 scenario 时清理

**问题**：如果用户手动创建了多个 legacy versions，可能不会自动清理

**建议**：在 TagService 中实现自动清理逻辑，每次创建新 scenario 时调用。

### 问题 4: 同步执行性能

**当前设计**：Scenario 之间同步执行

**问题**：如果 scenarios 很多，可能会很慢

**建议**：先实现同步，后续可以支持并行（通过配置或参数）。

---

## 最终推荐流程

基于你的描述和设计决策，最终流程如下：

### 阶段 1: TagManager 初始化

```python
tag_manager = TagManager(data_mgr=data_manager)
```

**执行内容**：
1. 从配置读取 scenarios 根目录
2. 初始化 TagService
3. **不在这里发现 scenarios**（延迟到 run() 时）

### 阶段 2: TagManager.run() 执行流程

```python
tag_manager.run(data_source_mgr=data_source_manager)
```

**执行内容**：
1. **发现 scenarios**：`_discover_and_register_calculators()`
   - 遍历 scenarios 目录
   - 加载 settings 和 calculator 类
   - 存储到缓存
2. **验证 settings**：`_validate_all_settings()`
   - 统一做 schema 校验
   - 抛出早期错误
3. **执行每个 calculator**：`for calc in self.calculators: calc.run()`
   - 同步执行（one by one）
   - 如果出错，记录日志但继续执行其他 scenarios

### 阶段 3: Calculator.run() 执行流程

```python
def run(self, data_source_mgr=None):
    # 1. 确保元信息存在
    self.ensure_metadata()
    
    # 2. 处理版本变更和更新模式
    self.renew_or_create_values()
```

#### 3.1 ensure_metadata()

```python
def ensure_metadata(self):
    # 1. 确保 scenario 存在
    scenario = self.ensure_scenario()
    
    # 2. 确保 tag definitions 存在
    tag_defs = self.ensure_tags(scenario)
    
    return scenario, tag_defs
```

**ensure_scenario()**：
- 查询数据库中该 scenario name 的所有版本
- 如果 settings.version 已存在：返回该 scenario
- 如果 settings.version 不存在：创建新的 scenario

**ensure_tags()**：
- 检查该 scenario 下的 tag definitions 是否存在
- 如果不存在，创建新的 tag definitions

#### 3.2 renew_or_create_values()

```python
def renew_or_create_values(self):
    # 1. 处理版本变更
    version_action = self.handle_version_change()
    
    # 2. 根据版本变更结果和 update_mode 计算
    self.handle_update_mode(version_action)
```

**handle_version_change()**：
- 查询数据库中该 scenario name 的所有版本
- 如果 settings.version 在数据库中已存在：`version_action = "NO_CHANGE"`
- 如果 settings.version 不在数据库中：
  - `version_action = on_version_change`（REFRESH_SCENARIO 或 NEW_SCENARIO）
  - 如果是 NEW_SCENARIO：创建新 scenario，标记旧的为 legacy，清理旧版本（>= 3）
  - 如果是 REFRESH_SCENARIO：更新 scenario，删除旧的 tag definitions，创建新的

**handle_update_mode(version_action)**：
- 如果 `version_action == "NO_CHANGE"`：按 `update_mode` 计算（INCREMENTAL 或 REFRESH）
- 如果 `version_action == "NEW_SCENARIO"` 或 `"REFRESH_SCENARIO"`：重新计算所有 tags

### 阶段 4: 手动注册 Scenario（未来实现）

```python
tag_manager.register_scenario(settings_dict)
```

**设计目标**：支持"隐形"的 tag 计算器（没有 settings 文件）

**实现方式**：
- 验证 settings_dict
- 创建 calculator 实例
- 调用 calculator.run()

---

## 关键设计点总结

1. **元信息创建在 Calculator**：支持手动注册 scenarios，设计灵活
2. **Settings 验证在 TagManager**：统一做 schema 校验，抛出早期错误
3. **Legacy Version 清理**：保留 active version + 最多 N 个 legacy versions（默认 N=3）
4. **同步执行**：Scenario 之间同步执行，Calculator 内部多线程
5. **Version 对比逻辑**：每次执行时都检查，确保一致性

---

## 设计决策和上下文

### 1. 为什么元信息创建放在 Calculator 里？

**设计目标**：支持手动 `register_scenario`，允许用户传入 settings 字典（没有 settings 文件），创建"隐形"的 tag 计算器。

**实现方式**：
- 元信息的创建流程滞后，放在 `Calculator.run()` 中处理
- `TagManager.register_scenario(settings_dict)` 只做必须的验证和注册
- 这样既支持文件系统发现的 scenarios，也支持手动注册的 scenarios

**职责划分**：
- **TagManager**：发现 scenarios、验证 settings（`_validate_all_settings()`）、管理 calculator 实例
- **Calculator**：确保元信息存在（`ensure_metadata()`）、处理版本变更、执行计算

### 2. Settings 验证的位置

**设计决策**：`_validate_all_settings()` 放在 TagManager 层

**原因**：
- 统一做 schema 校验，抛出早期错误
- 在 `run()` 之前就发现配置问题，避免运行时错误
- 支持手动 `register_scenario` 时的验证

### 3. Legacy Version 清理策略

**设计决策**：每个 scenario（name 相同，version 不同）存多个 scenario 记录

**原因**：
- 便于查询和管理不同版本
- 清理时只需要删除最老的 scenario 记录（及其关联的 tag definitions 和 tag values）
- 保留策略：active version + 最多 N 个 legacy versions（默认 N=3）

**清理逻辑**：
- 当创建新 scenario 时（NEW_SCENARIO），如果 legacy version 数量 >= max_versions，删除最老的
- 所有 version 变化都统一处理，无论是手动还是自动创建

### 4. 同步执行策略

**设计决策**：Scenario 之间同步执行（one by one）

**原因**：
- Calculator 内部已经是多线程的（对 entity 的计算）
- Scenario 之间再并行会太复杂，容易导致资源竞争
- 先实现同步，确保正确性

---

## 流程 Review 和问题分析

### ✅ 合理的部分

1. **延迟注册**：在 Calculator.run() 时检查并注册，避免初始化时的数据库操作
2. **Version 对比时机**：在 Calculator 的 `handle_version_change()` 中对比，每次执行时都检查
3. **Legacy 清理策略**：保留最多 3 个版本，自动清理最老的，合理
4. **同步执行**：Scenario 之间同步执行，简单可靠
5. **元信息创建在 Calculator**：支持手动注册 scenarios，设计灵活

### ⚠️ 需要注意的问题

#### 问题 1: REFRESH_SCENARIO 时是否删除 tag values？

**设计决策**：**删除旧的 tag values**

**原因**：
- 多个版本的 tag 可能会误导用户
- refresh 的目的是彻底刷新，删除后重新创建更清晰
- 避免数据混乱，确保数据一致性

**实现**：
- 在 REFRESH_SCENARIO 时，调用 `delete_tag_values_by_scenario()` 删除旧的 tag values
- 然后重新计算并创建新的 tag values

#### 问题 2: Version 对比的精确逻辑

**当前流程**：在 `handle_version_change()` 中对比

**逻辑**：
1. **如果 settings.version 在数据库中已存在且 is_legacy=0（active）**：
   - `version_action = "NO_CHANGE"`（版本未变，继续使用）

2. **如果 settings.version 在数据库中已存在但 is_legacy=1（legacy）**：
   - 这是用户把 version 改回到以前存在过的版本（版本回退）
   - **检查全局配置 `ALLOW_VERSION_ROLLBACK`**（默认 False）
   - 如果 `ALLOW_VERSION_ROLLBACK = False`：
     - 记录严重警告日志，明确告知风险
     - 抛出 ValueError，阻止继续执行
     - 用户需要明确配置 `ALLOW_VERSION_ROLLBACK = True` 才能继续
   - 如果 `ALLOW_VERSION_ROLLBACK = True`：
     - 记录警告日志，明确告知风险
     - 查找当前的 active 版本（is_legacy=0）
     - 如果存在 active 版本：
       - 标记之前的 active 版本为 legacy
     - 把当前版本（settings.version）设置为 legacy=0（active）
     - 注意：不删除旧的 tag definitions 和 tag values
     - 确保 tag definitions 存在
     - 按照该版本的 update_mode 继续（incremental 或 refresh）
     - `version_action = "ROLLBACK"`（版本回退，按照 update_mode 继续）

3. **如果 settings.version 在数据库中不存在**：
   - 读取 on_version_change 配置
   - `version_action = on_version_change`（REFRESH_SCENARIO 或 NEW_SCENARIO）
   - 如果是 NEW_SCENARIO：创建新 scenario，标记旧的为 legacy，清理旧版本
   - 如果是 REFRESH_SCENARIO：更新 scenario，删除旧的 tag definitions 和 tag values，创建新的

**这个逻辑是合理的**，因为：
- 每次执行时都检查，确保一致性
- 支持动态修改 settings 中的 version
- 支持回退到以前的版本（legacy -> active），但有安全机制
- **安全机制**：默认不允许版本回退，需要用户明确配置
- **明确告知风险**：通过警告日志和配置要求，确保用户知晓风险

### 💡 优化建议

1. **错误处理**：每个 scenario 的计算错误不应该影响其他 scenarios
2. **日志记录**：详细记录每个步骤的执行情况（ensure_metadata, handle_version_change, cleanup_legacy_versions 等）
3. **进度跟踪**：可以添加进度回调，方便监控
4. **配置验证**：在 TagManager.run() 之前统一验证所有 settings（`_validate_all_settings()`）
