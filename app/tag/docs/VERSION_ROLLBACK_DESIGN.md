# 版本回退（Version Rollback）设计

本文档讨论版本回退的处理逻辑和设计决策。

---

## 问题背景

**场景**：用户把 version 从 "2.0" 改回 "1.0"（版本1已经存在且是 legacy）

**问题**：如何处理这种版本回退？

---

## 版本回退的意义

版本回退可能有以下几种意图：

1. **只读查看**：用户只想查看之前版本的 tag 计算结果，不重新计算
2. **算法回退**：用户想回退到之前的算法版本，需要重新计算
3. **数据对比**：用户想对比不同版本的计算结果

**关键问题**：
- 仅通过 `version` 字段无法完全保证算法的一致性
- 用户需要对自己的行为负责
- 系统需要提供清晰的警告和确认机制

---

## 设计方案对比

### 方案 A：不允许回退 legacy version（简单暴力）

**逻辑**：
- 如果 settings.version 在数据库中已存在但 is_legacy=1，抛出错误，不允许回退

**优点**：
- 简单，避免复杂逻辑
- 避免数据混乱

**缺点**：
- 如果用户真的就有之前的算法呢？结果我们堵死了他的路
- 不够灵活

**结论**：❌ 不推荐，太限制用户

---

### 方案 B：回退后第一次自动 refresh（逻辑复杂）

**逻辑**：
- 如果 settings.version 在数据库中已存在但 is_legacy=1：
  - 版本2变成 legacy
  - 版本1从 legacy 变成 active
  - **第一次自动 refresh**（删除旧数据，重新计算）
  - 后续按照 update_mode 继续

**优点**：
- 确保数据一致性
- 避免新旧数据混合

**缺点**：
- 逻辑复杂（需要区分"第一次"和"后续"）
- 会覆盖原数据（用户可能只是想查看）
- 如果用户只是想查看，却强制刷新了数据

**结论**：❌ 不推荐，逻辑复杂且可能不符合用户意图

---

### 方案 C：回退后按照该版本的 update_mode 继续（用户方案 + 安全机制）

**逻辑**：
- 如果 settings.version 在数据库中已存在但 is_legacy=1：
  - **检查全局配置 `ALLOW_VERSION_ROLLBACK`**（默认 False）
  - 如果 `ALLOW_VERSION_ROLLBACK = False`：
    - 记录严重警告日志，明确告知风险
    - 抛出 ValueError，阻止继续执行
    - 用户需要明确配置 `ALLOW_VERSION_ROLLBACK = True` 才能继续
  - 如果 `ALLOW_VERSION_ROLLBACK = True`：
    - 记录警告日志，明确告知风险
    - 版本2变成 legacy
    - 版本1从 legacy 变成 active
    - **按照版本1的 update_mode 继续跑**：
      - 如果是 incremental，继续 incremental
      - 如果是 refresh，就 refresh
    - 用户需要对自己的行为负责

**优点**：
- **安全机制**：默认不允许，需要用户明确配置
- **明确告知风险**：通过警告日志和配置要求，确保用户知晓风险
- 灵活，尊重用户的意图
- 逻辑简单，不需要区分"第一次"和"后续"
- 如果用户想回退算法，可以继续计算
- 如果用户只是想查看，可以设置 update_mode=INCREMENTAL（不会重新计算已有数据）

**缺点**：
- 如果版本1之前是 incremental 跑的，现在继续 incremental 跑，可能会和之前的 tag 结果不一致
- 但这是用户的选择，用户需要明确配置才能继续

**结论**：✅ **推荐**，符合用户意图，逻辑简单，且有安全机制

---

### 方案 D：回退后询问用户意图（交互复杂）

**逻辑**：
- 如果 settings.version 在数据库中已存在但 is_legacy=1：
  - 询问用户：只读查看 or 重新计算？
  - 根据用户选择执行

**优点**：
- 明确用户意图
- 避免误操作

**缺点**：
- 需要交互，不适合自动化场景
- 增加复杂度

**结论**：⚠️ 可以考虑作为可选项，但不作为默认方案

---

## 推荐方案：方案 C（按照该版本的 update_mode 继续 + 安全机制）

### 详细逻辑

```python
# 全局配置（app/tag/config.py）
ALLOW_VERSION_ROLLBACK = False  # 默认 False，需要用户明确配置为 True

def handle_version_change(self) -> str:
    # 1. 查询数据库中该 scenario name 的所有版本
    db_scenarios = self.tag_service.list_scenarios(
        scenario_name=self.scenario_name
    )
    
    # 2. 查找 settings.version 是否在数据库中已存在
    existing_scenario = None
    for s in db_scenarios:
        if s["version"] == self.scenario_version:
            existing_scenario = s
            break
    
    # 3. 如果已存在且 is_legacy=0（active）：
    if existing_scenario and existing_scenario["is_legacy"] == 0:
        version_action = "NO_CHANGE"
        return version_action
    
    # 4. 如果已存在但 is_legacy=1（legacy）：
    if existing_scenario and existing_scenario["is_legacy"] == 1:
        # 这是用户把 version 改回到以前存在过的版本（版本回退）
        
        # 检查全局配置
        from app.tag.config import ALLOW_VERSION_ROLLBACK
        
        if not ALLOW_VERSION_ROLLBACK:
            # 不允许版本回退，抛出异常
            error_msg = (
                f"Version rollback detected but not allowed: "
                f"scenario={self.scenario_name}, version={self.scenario_version}. "
                "Version rollback may cause data inconsistency. "
                "Only rollback version if calculator logic is also rolled back. "
                "To allow version rollback, set ALLOW_VERSION_ROLLBACK=True in app/tag/config.py"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 允许版本回退，但记录警告
        warning_msg = (
            f"Version rollback detected: "
            f"scenario={self.scenario_name}, version={self.scenario_version}. "
            "WARNING: Version rollback may cause data inconsistency. "
            "Only rollback version if calculator logic is also rolled back. "
            "User is responsible for ensuring algorithm consistency."
        )
        logger.warning(warning_msg)
        
        # 查找当前的 active 版本（is_legacy=0）
        active_scenario = None
        for s in db_scenarios:
            if s["is_legacy"] == 0:
                active_scenario = s
                break
        
        # 如果存在 active 版本，标记为 legacy
        if active_scenario:
            self.tag_service.mark_scenario_as_legacy(active_scenario["id"])
        
        # 把当前版本（existing_scenario）设置为 legacy=0（active）
        self.tag_service.update_scenario(
            existing_scenario["id"],
            is_legacy=0
        )
        
        # 注意：不删除旧的 tag definitions 和 tag values
        # 保留历史数据，让用户可以查看
        
        # 确保 tag definitions 存在
        self.ensure_tags(existing_scenario)
        
        version_action = "ROLLBACK"  # 新增一个 action
        return version_action
    
    # 5. 如果不存在：
    #    - 读取 on_version_change 配置
    #    - version_action = on_version_change（REFRESH_SCENARIO 或 NEW_SCENARIO）
    #    ...
```

### 关键点

1. **不删除旧数据**：
   - 不删除旧的 tag definitions 和 tag values
   - 保留历史数据，让用户可以查看

2. **按照该版本的 update_mode 继续**：
   - 如果该版本之前是 incremental，继续 incremental（从上次计算的最大 as_of_date 继续）
   - 如果该版本是 refresh，就 refresh（重新计算所有数据）

3. **用户需要对自己的行为负责**：
   - 如果版本1之前是 incremental 跑的，现在继续 incremental 跑，可能会和之前的 tag 结果不一致
   - 但这是用户的选择，用户需要明确知道这个风险

4. **新增 VersionAction**：
   - 新增 `"ROLLBACK"` action，区别于 `"NO_CHANGE"`、`"NEW_SCENARIO"`、`"REFRESH_SCENARIO"`

---

## 实现细节

### 1. 获取该版本的 update_mode

**问题**：如何获取该版本的 update_mode？

**方案 A**：从 settings 中读取（当前 settings 的 update_mode）
- 优点：简单
- 缺点：如果用户修改了 settings 中的 update_mode，可能和之前不一致

**方案 B**：从数据库中存储（在 scenario 或 tag_definition 中存储 update_mode）
- 优点：准确，记录历史配置
- 缺点：需要修改数据库 schema

**方案 C**：从 settings 中读取，但记录警告日志
- 优点：简单，但提醒用户可能不一致
- 缺点：用户可能忽略警告

**推荐**：方案 C（从 settings 中读取，但记录警告日志）

### 2. handle_update_mode 的处理

```python
def handle_update_mode(self, version_action: str):
    if version_action == "NO_CHANGE":
        # 按 update_mode 计算（INCREMENTAL 或 REFRESH）
        update_mode = self.performance.get("update_mode", "INCREMENTAL")
        if update_mode == "INCREMENTAL":
            # 从上次计算的最大 as_of_date 继续
            start_date = self._get_max_as_of_date(tag_defs) + 1
            end_date = self._get_latest_trading_date()
        elif update_mode == "REFRESH":
            # 从 start_date 到 end_date
            start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
            end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
    
    elif version_action == "ROLLBACK":
        # 按照该版本的 update_mode 继续
        update_mode = self.performance.get("update_mode", "INCREMENTAL")
        
        # 记录警告日志
        logger.warning(
            f"Version rollback detected: scenario={self.scenario_name}, "
            f"version={self.scenario_version}. "
            f"Continuing with update_mode={update_mode}. "
            f"User is responsible for ensuring algorithm consistency."
        )
        
        if update_mode == "INCREMENTAL":
            # 从上次计算的最大 as_of_date 继续
            start_date = self._get_max_as_of_date(tag_defs) + 1
            end_date = self._get_latest_trading_date()
        elif update_mode == "REFRESH":
            # 重新计算所有数据
            start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
            end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
    
    elif version_action == "NEW_SCENARIO" or version_action == "REFRESH_SCENARIO":
        # 重新计算所有 tags
        start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
        end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
    
    # 执行计算...
```

---

## 总结

**推荐方案**：方案 C（按照该版本的 update_mode 继续 + 安全机制）

**关键点**：
1. **全局配置 `ALLOW_VERSION_ROLLBACK`**（默认 False）：
   - 用户需要明确配置为 True 才能允许版本回退
   - 确保用户知晓风险
2. **明文警告**：
   - 如果配置为 False，抛出 ValueError，明确告知风险
   - 如果配置为 True，记录警告日志，明确告知风险
3. 版本回退后，不删除旧数据
4. 按照该版本的 update_mode 继续（incremental 或 refresh）
5. 用户需要对自己的行为负责

**优点**：
- **安全机制**：默认不允许，需要用户明确配置
- **明确告知风险**：通过警告日志和配置要求，确保用户知晓风险
- 灵活，尊重用户的意图
- 逻辑简单，不需要区分"第一次"和"后续"
- 如果用户想回退算法，可以继续计算
- 如果用户只是想查看，可以设置 update_mode=INCREMENTAL（不会重新计算已有数据）

**缺点**：
- 如果版本1之前是 incremental 跑的，现在继续 incremental 跑，可能会和之前的 tag 结果不一致
- 但这是用户的选择，用户需要明确配置才能继续

**实现建议**：
1. 在 `app/tag/config.py` 中添加 `ALLOW_VERSION_ROLLBACK = False`
2. 在 `handle_version_change()` 中检查配置
3. 如果配置为 False，抛出 ValueError，明确告知风险
4. 如果配置为 True，记录警告日志，继续执行
5. 在文档中明确说明版本回退的行为和风险
