## BaseHandler v2 改造计划 & 差异对照

本文档总结 data_source 模块从旧版 `BaseDataSourceHandler` 管线迁移到新版 `BaseHandler` 管线时，需要保留 / 补齐的能力，以及各层的职责划分，作为后续实现的参考 checklist。

---

## 一、执行流程与钩子对齐

### 1. 细分执行阶段钩子（Execution Hooks）

**旧版具备**

- `before_all_tasks_execute(tasks, context)`
- `before_single_task_execute(task, context)`
- `after_single_task_execute(task_id, task_result, context)`
- `after_all_tasks_execute(task_results, context)`

**新版现状**

- 只有聚合粒度的 `on_fetch(context, apis)`，内部直接调度 `ApiJobScheduler`，未暴露阶段/单元级别的钩子。

**计划**

- 在 `BaseHandler` 中补齐一组等价语义的钩子，基于“批次/阶段/ApiJob”而不是旧的 Task 概念，例如：
  - `on_before_all_batches_execute(batches, context)`
  - `on_before_single_batch_execute(batch, context)`
  - `on_after_single_batch_execute(batch_id, batch_result, context)`
  - `on_after_all_batches_execute(all_results, context)`
- 在 `on_fetch` 内部（或 Scheduler 层）按执行阶段调用这些钩子，默认实现是 no-op，供复杂 Handler 覆盖使用。

### 2. 错误处理钩子（Error Hook）

**旧版具备**

- `on_error(error, context)`：统一的错误处理入口，`execute()` 顶层捕获异常后调用。

**新版现状**

- `BaseHandler.execute()` 目前没有显式错误钩子，只是让异常自然向上抛出。

**计划**

- 在 `BaseHandler` 中增加 `on_error(error: Exception, context: Dict[str, Any])`：
  - 默认实现：记录日志并重抛；
  - 子类可以在此实现定制告警 / 清理逻辑。
- 在 `execute()` 顶层用 `try/except` 包裹整个 pipeline，出错时调用 `on_error` 再决定是否重抛。

### 3. 执行尾部的数据验证（Validation at Pipeline End）

**旧版具备**

- 在 `execute()` 尾部调用 `validate(normalized_data)`，失败则抛 `ValueError`。
- 验证逻辑由 `DataValidator` + `schema` 负责。

**新版现状**

- `DataSourceSchema.validate_data()` 与 `DataValidator` 仍然存在，但 `BaseHandler.execute()` 没有统一的“执行尾校验”步骤。

**计划**

- 在 `BaseHandler.execute()` 的最后一步：
  - 使用 `DataValidator.validate(self.normalized_data, schema)`（或直接遍历 `schema.validate_data(record)`）进行统一校验；
  - 校验失败时抛出 `ValueError`，与旧版语义保持一致。

### 4. 细化钩子粒度，避免“一刀切”大钩子（Hook Granularity Control）

**问题分析**

- 当前 `on_fetch(context, apis)` 过于粗粒度，包含多个步骤：
  1. 构造 `ApiJobBatch`
  2. 创建 `ApiJobScheduler`
  3. 处理异步执行（事件循环兼容）
  4. 提取结果
- 如果用户只想修改其中一小步（例如 batch 构建逻辑、调度参数），却需要重写整个 `on_fetch`：
  - 难以复用默认行为（需要理解整个流程）
  - 容易破坏后续数据流（返回格式不匹配）
  - 维护成本高（默认实现更新时，用户代码可能失效）

**设计原则**

- **主流程固定**：`execute()` 的步骤顺序不变，保证流程稳定性
- **细粒度钩子**：每个钩子只负责一个步骤，scope 小、复杂度低
- **默认实现 + 可覆盖**：每个钩子都有默认实现，用户可以选择性覆盖
- **统一命名**：所有钩子使用 `on_xxx` 命名约定

**计划**

- 将 `on_fetch` 拆解成多个细粒度钩子，每个钩子只负责一个步骤：
  ```python
  def on_fetch(self, context, apis):
      # 步骤 1：构造 batch（可覆盖）
      batch = self.on_build_batch(context, apis)
      
      # 步骤 2：batch 执行前增强钩子（可选）
      batch = self.on_before_batch_execute(context, batch)
      
      # 步骤 3：执行 batch（可覆盖）
      exec_result = self.on_execute_batch(context, batch)
      
      # 步骤 4：batch 执行后增强钩子（可选）
      exec_result = self.on_after_batch_execute(context, exec_result, batch)
      
      # 步骤 5：提取结果（可覆盖）
      return self.on_extract_fetch_results(context, exec_result, batch)
  ```

- 钩子定义（所有钩子使用 `on_xxx` 命名）：
  - `on_build_batch(context, apis) -> ApiJobBatch`：构造 ApiJobBatch（有默认实现，可覆盖）
  - `on_before_batch_execute(context, batch) -> ApiJobBatch`：batch 执行前的增强钩子（默认返回 batch，可覆盖用于修改 batch）
  - `on_execute_batch(context, batch) -> Dict[str, Any]`：执行 batch，调用 Scheduler（有默认实现，可覆盖）
  - `on_after_batch_execute(context, exec_result, batch) -> Dict[str, Any]`：batch 执行后的增强钩子（默认返回 exec_result，可覆盖用于修改结果）
  - `on_extract_fetch_results(context, exec_result, batch) -> Dict[str, Any]`：从执行结果中提取 fetch 阶段的数据（有默认实现，可覆盖）

- 优势：
  - ✅ 粒度小：每个钩子只做一件事，易于理解和维护
  - ✅ 易复用：用户只需覆盖需要的步骤，其他自动使用默认实现
  - ✅ 更安全：不会因为重写导致整个流程失效
  - ✅ 更灵活：可以在默认基础上增强，而不是完全替换

- 同样原则适用于其他大钩子：
  - `on_normalize` 也可以拆解为多个小钩子（字段映射、schema 应用、数据包装等）
  - 保持每个钩子的 scope 和复杂度在可控范围内

---

## 二、Config / Schema data class 职责

### 4. Config 访问与校验（DataSourceConfig）

**旧版具备**

- 通过 `get_param(key, default)`、`get_handler_config()` 访问配置；
- 部分 renew 相关必填字段在执行时（如 renew service）才发现缺失。

**新版现状**

- 引入 `DataSourceConfig`：
  - 从 `config.json` 构造；
  - 在 `__init__` / `validate()` 中验证 `renew_mode` 相关必填字段；
  - 提供若干访问方法：`get_renew_mode()`、`get_date_format()`、`get_table_name()` 等。
- `DataSourceManager._discover_config()` 已经返回 `DataSourceConfig` 实例，而不是裸 dict。

**计划**

- 统一约定：**所有 config 读取都通过 `DataSourceConfig` 方法完成**：
  - 新增或完善接口：`get_default_date_range()`、`get_rolling_unit()`、`get_rolling_length()`、`get_apis()` 等；
  - 检查 `BaseHandler` / `RenewService` / 其他 service 中对 config 的访问，替换为 `DataSourceConfig` API（保留对 dict 的兼容逻辑作为兜底）。
- 在发现阶段（`_discover_config`）**强制调用 `config.validate()`**，保证配置问题一开始就 fail fast。

### 5. Schema 级验证（DataSourceSchema）

**旧版具备**

- `DataSourceSchema.validate(data)`：
  - 同时承担“验证 schema 本身”与“验证单条数据”两种职责（耦合度偏高）。

**新版现状**

- 将职责拆分为：
  - `DataSourceSchema.validate()`：验证 schema 自身完整性（name 非空、fields 非空等）；
  - `DataSourceSchema.validate_data(record)`：验证单条记录是否符合 schema；
  - `DataValidator` 负责批量数据的校验。
- `DataSourceManager._discover_schema()` 在发现后调用 `schema.validate()`，确保 schema 本身正确。

**计划**

- 检查并统一所有对旧 `schema.validate(...)` 的调用：
  - 数据校验使用 `validate_data()` / `DataValidator.validate()`；
  - schema 完整性校验只在发现阶段调用 `validate()`。

---

## 三、ApiJob / 执行计划相关工具

### 6. ApiJob 构造与管理职责（Handler vs Helper vs Data Class）

**旧版具备**

- `BaseDataSourceHandler` 内部提供：
  - `get_api_job(name)` / `get_api_job_with_params(name, params, job_id)`；
  - `create_simple_task(...)` / `get_simple_result(...)` 等辅助。

**新版现状**

- ApiJob 的构造主要集中在 `DataSourceHandlerHelper.build_api_jobs(apis_conf)`：
  - 从 config 的 `apis` 字段生成 `List[ApiJob]`；
  - 限流信息（`max_per_minute`）、依赖关系（`depends_on`）等在这里完成包装。
- `BaseHandler` 只做：
  - `_config_to_api_jobs()`：调用 helper 将 config → `List[ApiJob]`；
  - 保存 `self.apis`，并在 `on_before_fetch` / `on_fetch` 之间传递。

**计划**

- 明确职责边界：
  - Handler：描述执行流程（“先构造 jobs，再按 renew 决定日期，再交给 scheduler 执行”），不直接操纵内部 ApiJob 细节；
  - Helper / Data Class：负责解析 config、创建 ApiJob、后续如有需要可以提供按 name/join/merge 等操作的工具函数。
- 后续如发现 **“查找单个 ApiJob”** 等需求，再在 helper 层加聚合工具，而不是塞回 `BaseHandler`。

---

## 四、全局依赖与测试参数（后续增强）

### 7. 全局依赖注入（Global Dependencies）

**旧版具备**

- 通过 `DataManager` / 其他 Service 间接实现了一些全局依赖（如交易日历、stock list 等），但没有一个显式的“全局依赖注入”接口。

**新版现状**

- `BaseHandler.context["data_manager"] = DataManager.get_instance()`，为 renew / 其他步骤提供 DB 能力；
- 尚未定义统一的「全局业务依赖」注入约定，例如：
  - `context["globals"]["stock_list"]`
  - `context["globals"]["calendar"]` 等。

**计划**

- 在 `DataSourceManager` 或更高层的 project context 设计一个「全局依赖对象」注入协议：
  - Manager 负责组装 `context["globals"]`；
  - Handler 只通过约定好的 key 读取（或通过 config 声明依赖）。
- 这一块可以在 BaseHandler v2 主线稳定后再补。

### 8. 测试参数（dry_run / test_mode）

**旧版具备**

- 通过 config + `BaseDataSourceHandler.execute()` 合并：
  - `dry_run`：干运行模式，主要影响数据保存；
  - `test_mode`：测试模式。

**新版现状**

- 暂未实现这两个参数的统一支持。

**计划（延后）**

- 在新版 config 体系稳定后，为 `DataSourceConfig` 或更高层 config 增加 `dry_run` / `test_mode` 字段；
- 由 `DataSourceManager` 在组装 context 时注入，并在 Handler / 保存层按需使用。

---

## 五、数据保存辅助（仅保留纯清洗逻辑）

### 9. clean_nan 等通用清洗行为

**旧版具备**

- `_validate_data_for_save(normalized_data)`：验证 `{"data": [...]}` 结构；
- `_save_data_with_clean_nan(normalized_data, context, save_method, data_source_name)`：
  - 使用 `DBHelper.clean_nan_in_list` 清理 NaN；
  - 调用具体的 `save_method` 落库；
  - 支持 `dry_run` 模式。

**新版现状**

- BaseHandler 明确**不负责存储**，但还没有一个重新安置 clean_nan 这类“纯清洗工具”的位置。

**计划**

- 将 `clean_nan` 这类函数下沉到独立的 util（例如 `DBHelper` / `DataFrameHelper` / 独立 module）：
  - 保留“清洗逻辑”，去掉“具体保存逻辑”的耦合；
  - 需要保存的 Handler 或上层组件按需调用这些 util。
- BaseHandler 不再引入直接的“保存”语义，保持“获取 + 标准化”的纯度。

---

## 六、实现优先级建议（明日工作顺序）

1. **BaseHandler：细化钩子粒度 + 补齐执行阶段细分钩子 + `on_error` + 执行尾部数据验证**  
   - **优先处理钩子粒度问题**：将 `on_fetch` 等大钩子拆解为细粒度钩子，确保每个钩子 scope 小、复杂度低
   - 补齐执行阶段细分钩子（batch 级别）
   - 添加 `on_error` 统一错误处理
   - 执行尾部数据验证
   - 这是整个 pipeline 的主干，对可观察性、安全性和可维护性影响最大

2. **Config / Schema：稳定 DataSourceConfig / DataSourceSchema 的职责与 API**  
   - 确保所有 config/schema 相关访问统一通过 data class 完成，发现阶段完成 validate，执行阶段只消费

3. **ApiJob / Executor：根据需要扩展 helper 工具，而不是回退到 Handler 层**  
   - 保持 BaseHandler 简洁，突出“步骤大纲 + 细粒度钩子”，复杂逻辑继续沉到 service/helper

4. **全局依赖注入 & 测试参数 & 数据清洗 util**  
   - 视项目节奏在后续迭代中补充

