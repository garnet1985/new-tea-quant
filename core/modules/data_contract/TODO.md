# Data Contract Module TODO

## 当前状态
- ✅ BaseDataKey（meta/runtime/specific三层结构）
- ✅ BaseDataKeyLoader（load/load_batch）
- ✅ Declaration文件（16个 data_keys 全部完成）
- ✅ Runtime注入（add_runtime/fill_in_data参数）
- ✅ ContractRuntime动态字段（adjust, amount等）
- ✅ ContractPool（发现机制）
- ✅ Contract ID（唯一标识符）
- ✅ Runtime Fingerprint（缓存标识）
- ✅ is_customized字段（系统=False，用户=True）
- ✅ 清理旧代码（删除所有 key.py）
- ✅ Merge CacheManager到BaseDataKey

## 待实现功能（按优先级）

### 1. 发现机制（Discovery）- 高优先级 ✅ 已完成
- [x] ContractPool/Registry（合约池）
  - [x] 扫描系统 declaration 文件（data_keys/*/declaration.py）
  - [x] 建立 data_key → declaration 映射（18个）
  - [x] 加载 loader（从 declaration）
  - [x] 验证继承关系（loader 必须继承 BaseDataKeyLoader）
  - [x] 验证必要字段（data_key, type, scope）
  - [x] 设置 is_customized（系统=False，用户=True）
- [x] 发现 API
  - [x] get_contract(data_key) → Contract 实例
  - [x] list_available_data_keys() → 可用 data_key列表
  - [x] list_system_data_keys() → 系统 data_keys
  - [x] list_user_data_keys() → 用户 data_keys
  - [x] is_customized(data_key) → 是否用户自定义
  - [x] register_custom_declaration(declaration) → 注册自定义
- [x] 清理旧代码
  - [x] 删除所有 key.py（16个）
  - [x] 删除旧 discovery.py
  - [x] 更新所有 loader.py 导入路径
  - [x] 验证测试通过

### 2. 缓存管理（Cache）- 高优先级 ✅ 已完成（简化设计）
- [x] 缓存设计理念
  - [x] Contract.data 存储数据（这就是 cache）
  - [x] Contract.runtime_fingerprint 管理缓存标识
  - [x] Contract.is_loaded 判断是否有数据和缓存
  - [x] Contract.is_runtime_updated 判断是否需要验证
  - [x] 不需要外部管理器（Contract 内部处理）
- [x] Runtime Fingerprint
  - [x] 由 runtime 决定（包含所有 runtime 字段）
  - [x] SHA256 计算
  - [x] 只在 runtime 更新时验证（已加载 + runtime 更新）
- [x] 缓存逻辑
  - [x] 未加载：直接加载（不验证 fingerprint）
  - [x] 已加载 + runtime 未更新：直接返回（使用 cache）
  - [x] 已加载 + runtime 更新：验证 fingerprint
    - [x] fingerprint 未变：直接返回（使用 cache）
    - [x] fingerprint 已变：重新加载
- [x] 简化设计
  - [x] Merge ContractCacheManager 到 BaseDataKey
  - [x] 移除外部缓存管理器
  - [x] 移除不靠谱的检查
  - [x] 只保留必要方法

### 3. 数据注入管理（Issue Manager）- 中优先级 ✅ 不需要（已简化）
- [x] ~~DataContractManager~~（ContractPool 已替代）
  - [x] ~~mapping合并（system + user）~~（不需要 mapping 概念）
  - [x] ~~issue/load API~~（fill_in_data 内部消化）
  - [x] ~~批量contract管理~~（ContractPool 已提供）
- [x] ~~Facade API（contracts.py）~~（ContractPool 已提供统一入口）
  - [x] ~~issue(data_key, runtime) → Contract~~（pool.get_contract + fill_in_data）
  - [x] ~~load(contract) → 数据~~（contract.fill_in_data）
  - [x] ~~batch_load(contracts) → 批量加载~~（用户自行循环）

### 4. 时间辅助工具（Time Helpers）- 低优先级 ✅ 已完成
- [x] ContractTimeHelper（集成到 BaseTimeSeriesContract）
  - [x] time_axis_field/format获取（get_base_time_field, get_time_format）
  - [x] 时间格式转换（YYYYMMDD/YYYY-MM-DD/YYYYQ）（normalize_as_of）
  - [x] normalize_as_of（时间标准化）
- [x] 两个基类设计（方案1）
  - [x] BaseTimeSeriesContract（时序基类，扩展时间辅助工具）
  - [x] BaseNonTimeSeriesContract（非时序基类，无时间辅助工具）
  - [x] ContractPool 根据 contract_type 选择基类

### 5. 数据生命周期管理（Lifecycle）- 低优先级 ⏸️ 暂缓
- ⏸️ merge（合并数据）
  - ⏸️ append-tail merge
  - ⏸️ 时间序列合并
- ⏸️ drop（删除数据）
  - ⏸️ drop_before（释放内存）
- ⏸️ extend（扩展数据）
  - ⏸️ 动态加载新数据
**注**：暂时不做，因为没有实际 case，等有需求时再实现。

### 6. 数据验证（Validation）- 低优先级 ✅ 已完成
- ✅ validate_declaration（声明完整性检查）
  - ✅ ContractIssuer._validate_declaration_meta()（检查 meta 必要字段：key, type, scope）
  - ✅ BaseDataContract.validate_declaration()（检查 meta 字段）
  - ✅ 入口把关（在发现时自动验证）
- ✅ validate_runtime（运行时参数检查）
  - ✅ BaseDataContract._validate_runtime()（检查 entity_ids, start_time, end_time）
  - ✅ TagContract.validate_runtime()（检查 scenario）
- ❌ validate_raw（原始数据验证）**不实现**
  - 数据正确性由 loader 保证，contract 不验证数据格式
  - 避免过度复杂，用户通过测试确保 loader 返回正确数据

### 7. until 功能（基于 DataCursor）- 低优先级 ✅ 已实现
- ✅ until（单 contract until）
  - ✅ DataContracts.until(contract, as_of) → UntilResult
  - ✅ 基于 DataCursor 实现
  - ✅ 支持 per_entity
- ✅ until_cursor（多源 until）
  - ✅ open_until_cursor(name, contracts) → 绑定会话
  - ✅ until_cursor(name, as_of) → 推进时间点
  - ✅ reset_until_cursor_session(name) → 重置扫描状态
  - ✅ close_until_cursor(name) → 关闭会话
- ✅ 底层实现
  - ✅ DataCursor.until(as_of) → 返回累计前缀视图
  - ✅ 支持 per_entity（按 entity 分组）
  - ✅ ContractTimeHelper.normalize_as_of() → 时间标准化

### 8. 时间辅助工具（Time Helpers）- 低优先级 ✅ 已完成
- ✅ ContractTimeHelper（集成到 BaseTimeSeriesContract）
  - ✅ time_axis_field/format获取（get_base_time_field, get_time_format）
  - ✅ 时间格式转换（YYYYMMDD/YYYY-MM-DD/YYYYQ）（normalize_as_of）
  - ✅ normalize_as_of（时间标准化）
- ✅ 两个基类设计（方案1）
  - ✅ BaseTimeSeriesContract（时序基类，扩展时间辅助工具）
  - ✅ BaseNonTimeSeriesContract（非时序基类，无时间辅助工具）
  - ✅ ContractIssuer 根据 contract_type 选择基类

### 7. 其他优化
- [ ] ContractMeta添加更多字段（attrs等）
- [ ] 支持context参数（loader上下文）
- [ ] 错误处理和日志

## 当前任务
**已完成：发现机制 + 缓存管理（简化设计）**
- [x] 批量创建16个 declaration.py
- [x] 批量删除所有 key.py
- [x] 更新所有 loader.py 导入路径
- [x] 更新所有 __init__.py
- [x] 删除旧的 discovery.py
- [x] 实现发现机制（ContractPool）
- [x] 实现 runtime_fingerprint（缓存标识）
- [x] 实现 is_customized（系统/用户区分）
- [x] Merge CacheManager 到 BaseDataKey
- [x] 验证新的发现机制和缓存逻辑

## 下一步

**已完成功能**（优先级高→低）：
1. ✅ Contract 基类设计（meta/runtime/specific 三层结构）
2. ✅ 发现机制（ContractIssuer）
3. ✅ 数据注入管理（简化设计，不需要 DataContractManager）
4. ✅ 时间辅助工具（BaseTimeSeriesContract）
5. ✅ 缓存管理（内部缓存，runtime_fingerprint）
6. ✅ until 功能（基于 DataCursor）
7. ✅ 数据验证（入口把关 + runtime验证）
8. ✅ 命名修正（DataKey → DataContract, data_key → key）

**暂缓功能**（等实际 case）：
- ⏸️ 数据生命周期管理（merge/drop/extend）

**不实现功能**：
- ❌ validate_raw（数据正确性由 loader 保证）

**可选优化**（根据实际需求）：
- Facade API 完善（如果发现 legacy 有更多高价值 API）
- 性能优化（批量加载、缓存策略等）

**当前状态**：data_contract 核心功能已基本完成，可以开始集成到回测器和其他模块。
**可选：数据注入管理或其他功能**
- 实现时间辅助工具
- 实现数据生命周期管理
- 或根据实际需求调整优先级