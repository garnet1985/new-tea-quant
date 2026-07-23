# Data Contract Module TODO

## 当前状态
- ✅ BaseDataContract（meta/runtime/specific 三层结构）
- ✅ BaseDataContractLoader（load/load_batch）
- ✅ Declaration 文件（16个 data_contracts 全部完成）
- ✅ Runtime 注入（add_runtime/fill_in_data 参数）
- ✅ ContractRuntime 动态字段（adjust, amount等）
- ✅ ContractIssuer（发现机制）
- ✅ Contract ID（唯一标识符）
- ✅ Runtime Fingerprint（缓存标识）
- ✅ is_customized 字段（系统=False，用户=True）
- ✅ until/reset_cursor（PIT 数据裁剪，内置 cursor）
- ✅ 清理所有 legacy 代码和测试
- ✅ API 契约测试（65个测试全部通过）

## 已完成功能

### 1. 核心设计 ✅
- ✅ Contract 三层结构（meta/runtime/specific）
- ✅ 两个基类设计（BaseTimeSeriesContract/BaseNonTimeSeriesContract）
- ✅ Loader基类（BaseDataContractLoader）
- ✅ Declaration 文件（16个系统 contract）

### 2. 发现机制 ✅
- ✅ ContractIssuer（扫描 declaration 文件）
- ✅ 自动验证（meta字段、loader继承）
- ✅ 防止重复声明
- ✅ 根据contract_type 选择基类
- ✅ API：get_contract, list_available_keys, is_customized

### 3. 数据加载 ✅
- ✅ fill_in_data（自动选择 load/load_batch）
- ✅ 统一数据格式（per_entity scope 返回 dict[entity_id: data]）
- ✅ fingerprint 缓存（避免重复加载）
- ✅ 链式调用支持

### 4. 时间辅助工具 ✅
- ✅ get_base_time_field（获取时间字段）
- ✅ get_time_format（获取时间格式）
- ✅ normalize_as_of（时间标准化，YYYYMMDD）
- ✅ get_time_window（时间窗口）

### 5. until 功能 ✅
- ✅ until(as_of)（PIT 累计数据）
- ✅ reset_cursor()（重置 cursor）
- ✅ CursorState（独立cursor 状态）
- ✅ 累进扫描（总体 O(n)）
- ✅ 内存高效（引用共享，不复制数据）
- ✅ API 文档和测试

### 6. 数据验证 ✅
- ✅ validate_declaration（入口把关）
- ✅ validate_runtime（运行时验证）
- ❌ validate_raw（不实现，数据正确性由 loader 保证）

### 7. 测试和文档 ✅
- ✅ API 契约测试（test_api.py，65个测试）
- ✅ 测试用例文档（test_cases.yaml）
- ✅ API 文档（api.yaml）
- ✅ 清理 legacy 测试文件（删除8个文件）

### 8. 命名修正 ✅
- ✅ DataKey → DataContract
- ✅ data_key → key
- ✅ ContractPool → ContractIssuer
- ✅ BaseDataKeyLoader → BaseDataContractLoader

## 暂缓功能（等实际 case）

### 数据生命周期管理 ⏸️
- ⏸️ merge（合并数据）
- ⏸️ drop（删除数据）
- ⏸️ extend（扩展数据）
- ⏸️ slice（切片数据，低频使用）

**注**：暂时不做，因为没有实际使用场景，等有需求时再实现。

## 不实现功能

### validate_raw ❌
- 数据正确性由 loader 保证
- Contract 不验证数据格式
- 避免过度复杂

## 可选优化（根据实际需求）

### 性能优化
- 批量加载优化
- 缓存策略优化
- 内存管理优化

### API 完善
- slice(start_time, end_time)（如果需要）
- 其他便捷 API（根据反馈）

### 其他
- ContractMeta 添加更多字段（attrs等）
- 支持 context 参数（loader 上下文）
- 错误处理和日志完善

## 当前状态总结

**data_contract 核心功能已全部完成**，包括：
1. ✅ Contract 三层结构设计
2. ✅ 发现机制（ContractIssuer）
3. ✅ 数据加载和缓存
4. ✅ until/reset_cursor（PIT 数据裁剪）
5. ✅ 时间辅助工具
6. ✅ API 契约测试（65个测试通过）
7. ✅ 清理所有 legacy 代码

**下一步**：
- 集成到回测器和其他模块
- 根据实际使用反馈调整
- 如有新需求，再实现暂缓功能