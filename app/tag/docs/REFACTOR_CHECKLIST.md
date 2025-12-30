# Tag 系统重构清单

**版本**: v1.0  
**创建日期**: 2025-12-29  

---

## 📋 概述

本次重构的目标是：
1. **明确职责划分**：TagManager 负责主进程逻辑（调度），BaseTagWorker 负责子进程逻辑（执行）
2. **改进多进程设计**：使用类实例作为 executor，而非静态方法
3. **简化架构**：让代码结构更清晰，更符合面向对象设计原则
4. **重命名类和文件**：
   - `BaseTagCalculator` → `BaseTagWorker`
   - 用户自定义 `Calculator` → `TagWorker`
   - `calculator.py` → `tag_worker.py`

---

## 🎯 重构任务清单

### 阶段 0: 类和文件重命名

#### 0.1 重命名 BaseTagCalculator 为 BaseTagWorker
**负责人**: BaseTagCalculator  
**任务**:
- [ ] 重命名类：`BaseTagCalculator` → `BaseTagWorker`
- [ ] 重命名文件：`base_tag_calculator.py` → `base_tag_worker.py`
- [ ] 更新所有导入语句（`from app.tag.base_tag_calculator import BaseTagCalculator` → `from app.tag.base_tag_worker import BaseTagWorker`）
- [ ] 更新所有文档中的引用
- [ ] 更新代码注释和变量名

**当前状态**: ❌ 未实现  
**依赖**: 无

---

#### 0.2 重命名用户自定义 Calculator 为 TagWorker
**负责人**: 所有 scenario 文件  
**任务**:
- [ ] 重命名所有 scenario 目录下的 `calculator.py` 为 `tag_worker.py`
- [ ] 重命名用户自定义类：`XxxCalculator` → `XxxTagWorker`（例如：`MomentumCalculator` → `MomentumTagWorker`）
- [ ] 更新所有继承语句（`class XxxCalculator(BaseTagCalculator)` → `class XxxTagWorker(BaseTagWorker)`）
- [ ] 更新 TagManager 中的文件查找逻辑（`_discover_and_register_workers()`）
- [ ] 更新 TagManager 中的 `_load_calculator()` 方法名和逻辑（改为 `_load_worker()`）
- [ ] 更新所有文档中的引用
- [ ] 更新代码注释和变量名（calculator → worker）
- [ ] 更新示例文件（example/calculator.py → example/tag_worker.py）

**当前状态**: ❌ 未实现  
**依赖**: 0.1 完成

**说明**：
- 新文件名 `tag_worker.py` 明确表示这是子进程 worker
- 新类名 `XxxTagWorker` 明确表示这是 tag worker，会在子进程中实例化
- 文件结构：`app/tag/scenarios/<scenario_name>/tag_worker.py`

---

### 阶段 1: 职责重新划分

#### 1.1 TagManager 职责扩展
**负责人**: TagManager  
**任务**:
- [ ] 在 `TagManager.run()` 中添加多进程调度逻辑
- [ ] 实现 `_build_entity_jobs()` 方法：为每个 entity 创建 job
- [ ] 实现 `_decide_max_workers()` 方法：根据 job 数量决定进程数
- [ ] 实现 `_execute_scenario()` 方法：执行单个 scenario 的多进程计算
- [ ] 调用 `ProcessWorker`，传入 Executor 类（不是静态方法）
- [ ] 监控执行进度，收集统计信息

**当前状态**: ❌ 未实现  
**依赖**: 0.1 完成

---

#### 1.2 BaseTagWorker 职责精简
**负责人**: BaseTagWorker  
**任务**:
- [ ] 移除 `handle_update_mode()` 中的多进程调度逻辑
- [ ] 移除 `_process_single_entity_job()` 静态方法
- [ ] 移除 `_build_entity_jobs()` 方法（移到 TagManager）
- [ ] 移除 `_decide_max_workers()` 方法（移到 TagManager）
- [ ] 移除 `_load_entity_data_in_process()` 静态方法
- [ ] 移除 `_create_calculator_instance_in_process()` 静态方法
- [ ] 移除 `_batch_save_tag_values()` 静态方法
- [ ] 移除 `_get_trading_dates_static()` 静态方法
- [ ] 保留 `handle_update_mode()` 但只负责确定日期范围（不包含多进程调度）
- [ ] 添加 `process_entity()` 方法：作为子进程 worker，处理单个 entity

**当前状态**: ❌ 需要重构  
**依赖**: 1.1 完成

---

### 阶段 2: 多进程执行重构

#### 2.1 ProcessWorker 集成
**负责人**: TagManager  
**任务**:
- [ ] 修改 `ProcessWorker` 调用方式：
  - 当前：传入静态方法 `_process_single_entity_job`
  - 目标：传入 TagWorker 类，ProcessWorker 在子进程中实例化
- [ ] 实现 job payload 结构：
  ```python
  {
      'entity_id': str,
      'entity_type': str,
      'scenario_name': str,
      'scenario_version': str,
      'tag_definitions': List[Dict],
      'tag_configs': List[Dict],
      'start_date': str,
      'end_date': str,
      'worker_class': Type[BaseTagWorker],  # 类，不是实例（重命名自 calculator_class/executor_class）
      'settings_path': str,
      'base_term': str,
      'required_terms': List[str],
      'required_data': List[str],
      'core': Dict,
  }
  ```
- [ ] 实现 ProcessWorker 的 executor wrapper：
  - 接收 TagWorker 类和 payload
  - 在子进程中实例化 TagWorker
  - 调用 `worker.process_entity(payload)`

**当前状态**: ❌ 需要实现  
**依赖**: 0.1, 0.2, 1.1, 1.2 完成

---

#### 2.2 BaseTagWorker.process_entity() 实现
**负责人**: BaseTagWorker  
**任务**:
- [ ] 实现 `process_entity(payload: Dict[str, Any]) -> Dict[str, Any]` 方法：
  - 作为子进程 worker 的入口
  - 处理单个 entity 的所有日期
  - 返回统计信息
- [ ] 方法流程：
  1. 从 payload 提取信息
  2. 加载 entity 全量数据（到 end_date）
  3. 获取交易日列表
  4. 遍历每个日期：
     - 过滤数据到 as_of_date
     - 对每个 tag 调用 `calculate_tag()`
     - 收集结果
  5. 批量存储结果
  6. 返回统计信息
- [ ] 确保 tracker 等实例变量在子进程中正常工作

**当前状态**: ❌ 需要实现  
**依赖**: 1.2 完成

---

### 阶段 3: 辅助方法重构

#### 3.1 数据加载方法
**负责人**: BaseTagWorker  
**任务**:
- [ ] 将 `_load_entity_data_in_process()` 改为实例方法 `_load_entity_data_for_entity()`
- [ ] 移除静态方法标记
- [ ] 使用 `self.data_mgr` 而非传入参数

**当前状态**: ❌ 需要重构  
**依赖**: 1.2 完成

---

#### 3.2 数据过滤方法
**负责人**: BaseTagWorker  
**任务**:
- [ ] 将 `_filter_data_to_date()` 改为实例方法（如果当前是静态方法）
- [ ] 确保方法在子进程中正常工作

**当前状态**: ✅ 已实现（需要检查是否为静态方法）  
**依赖**: 无

---

#### 3.3 批量存储方法
**负责人**: BaseTagWorker / TagService  
**任务**:
- [ ] 将 `_batch_save_tag_values()` 改为实例方法
- [ ] 使用 `self.tag_service` 而非传入参数
- [ ] 或者：在 TagService 中实现 `batch_save_tag_values()` 方法
- [ ] 确保批量存储逻辑正确

**当前状态**: ❌ 需要重构  
**依赖**: 1.2 完成

---

#### 3.4 交易日获取方法
**负责人**: BaseTagWorker  
**任务**:
- [ ] 将 `_get_trading_dates_static()` 改为实例方法 `_get_trading_dates()`
- [ ] 使用 `self.data_mgr` 而非传入参数
- [ ] 移除静态方法标记

**当前状态**: ❌ 需要重构  
**依赖**: 1.2 完成

---

### 阶段 4: 状态管理优化

#### 4.1 Tracker 使用优化
**负责人**: BaseTagWorker / User TagWorkers  
**任务**:
- [ ] 确保 `self.tracker` 在子进程中正常工作
- [ ] 验证 tracker 在 `process_entity()` 方法中跨日期使用
- [ ] 更新 MomentumTagWorker 使用 tracker（如果还未完成）
- [ ] 添加 tracker 使用示例和文档

**当前状态**: ⚠️ 部分完成（tracker 已添加，但需要验证在子进程中工作）  
**依赖**: 2.2 完成

---

### 阶段 5: 测试和验证

#### 5.1 单元测试
**负责人**: 测试团队  
**任务**:
- [ ] 测试 TagManager 的多进程调度逻辑
- [ ] 测试 BaseTagWorker.process_entity() 方法
- [ ] 测试 tracker 在子进程中的使用
- [ ] 测试数据加载和过滤
- [ ] 测试批量存储

**当前状态**: ❌ 未开始  
**依赖**: 阶段 1-4 完成

---

#### 5.2 集成测试
**负责人**: 测试团队  
**任务**:
- [ ] 测试完整的多进程执行流程
- [ ] 测试多个 scenario 的执行
- [ ] 测试错误处理（单个 entity 失败不影响其他）
- [ ] 测试内存使用（确保进程结束后释放）

**当前状态**: ❌ 未开始  
**依赖**: 阶段 1-4 完成

---

#### 5.3 性能测试
**负责人**: 测试团队  
**任务**:
- [ ] 测试多进程性能提升
- [ ] 测试内存使用情况
- [ ] 测试进程数对性能的影响
- [ ] 对比重构前后的性能

**当前状态**: ❌ 未开始  
**依赖**: 阶段 1-4 完成

---

## 📝 详细设计说明

### 新的执行流程

```
主进程（TagManager）:
  1. 发现和验证所有 scenarios
  2. 对每个 scenario：
     a. 确定计算日期范围（调用 worker.handle_update_mode()）
     b. 获取 entity 列表
     c. 构建 jobs（每个 entity 一个 job）
     d. 决定进程数
     e. 创建 ProcessWorker
     f. 执行 jobs（传入 TagWorker 类）
     g. 收集结果和统计信息

子进程（ProcessWorker）:
  1. 接收 job payload 和 TagWorker 类
  2. 实例化 TagWorker（在子进程中）
  3. 调用 worker.process_entity(payload)
  4. TagWorker 处理单个 entity 的所有日期
  5. 返回统计信息
```

### ProcessWorker Executor Wrapper

需要实现一个 wrapper 函数，用于 ProcessWorker：

```python
def tag_executor_wrapper(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    ProcessWorker 的 executor wrapper
    
    在子进程中实例化 Executor 并执行
    
    注意：文件名从 calculator.py 改为 executor.py，明确表示这是子进程 executor
    """
    executor_class = payload['executor_class']  # 重命名自 calculator_class
    settings_path = payload['settings_path']
    
    # 初始化 DataManager 和 TagService（子进程中）
    from app.data_manager import DataManager
    data_mgr = DataManager(is_verbose=False)
    tag_service = data_mgr.get_tag_service()
    
    # 实例化 Executor（在子进程中）
    executor = executor_class(
        settings_path=settings_path,
        data_mgr=data_mgr,
        tag_service=tag_service
    )
    
    # 调用 process_entity 方法
    return executor.process_entity(payload)
```

### BaseTagWorker.process_entity() 方法签名

```python
def process_entity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理单个 entity 的 tag 计算（子进程 worker）
    
    Args:
        payload: Job payload 字典，包含：
            - entity_id: 实体ID
            - entity_type: 实体类型
            - tag_definitions: Tag Definition 列表
            - tag_configs: Tag 配置列表
            - start_date: 起始日期
            - end_date: 结束日期
            - base_term: 基础周期
            - required_terms: 需要的其他周期
            - required_data: 需要的数据源
            - core: Worker core 配置
    
    Returns:
        Dict[str, Any]: 统计信息
            {
                'entity_id': str,
                'total_tags': int,
                'success': bool,
                'error': str (可选)
            }
    """
```

---

## 🔄 迁移步骤

### 步骤 1: 准备阶段
1. 备份当前代码
2. 创建新的分支
3. 更新设计文档

### 步骤 2: 类和文件重命名
1. 重命名 `BaseTagCalculator` → `BaseTagWorker`，`base_tag_calculator.py` → `base_tag_worker.py`
2. 重命名所有 `calculator.py` 为 `tag_worker.py`
3. 重命名用户自定义类：`XxxCalculator` → `XxxTagWorker`
4. 更新所有引用和文档
5. 更新 TagManager 的文件查找逻辑

### 步骤 3: TagManager 扩展
1. 实现多进程调度逻辑
2. 实现 job 构建和进程数决定
3. 实现 ProcessWorker 集成

### 步骤 4: BaseTagWorker 精简
1. 移除多进程调度逻辑
2. 实现 `process_entity()` 方法
3. 重构辅助方法（从静态方法改为实例方法）

### 步骤 5: 测试和验证
1. 单元测试
2. 集成测试
3. 性能测试

### 步骤 6: 文档更新
1. 更新 DESIGN.md
2. 更新代码注释
3. 更新使用示例

---

## ⚠️ 注意事项

1. **向后兼容性**：
   - 不需要考虑向后兼容（用户明确说明）
   - 所有 Calculator 相关代码都需要更新为 Worker

2. **错误处理**：
   - 确保错误处理逻辑正确
   - 单个 entity 失败不影响其他 entity

3. **性能**：
   - 确保重构后性能不下降
   - 验证多进程执行效率

4. **内存管理**：
   - 确保子进程结束后内存正确释放
   - 验证 tracker 不会导致内存泄漏

5. **测试覆盖**：
   - 确保所有关键路径都有测试覆盖
   - 特别是多进程执行流程

---

## 📚 相关文档

- [DESIGN.md](./DESIGN.md) - 完整设计文档
- [多进程执行设计](./DESIGN.md#多进程执行设计) - 多进程执行详细设计
- [职责边界](./DESIGN.md#职责边界) - 组件职责说明

---

## ✅ 完成标准

重构完成的标准：
1. ✅ 所有任务清单项完成
2. ✅ 所有测试通过
3. ✅ 性能不低于重构前
4. ✅ 文档更新完成
5. ✅ 代码审查通过
