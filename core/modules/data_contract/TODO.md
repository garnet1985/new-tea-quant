# Data Contract Module TODO

## 当前状态
- ✅ BaseDataKey（meta/runtime/specific三层结构）
- ✅ BaseDataKeyLoader（load/load_batch）
- ✅ Declaration文件（16个 data_keys 全部完成）
- ✅ Runtime注入（add_runtime/fill_in_data参数）
- ✅ ContractRuntime动态字段（adjust, amount等）
- ✅ ContractPool（发现机制）
- ✅ 清理旧代码（删除所有 key.py）

## 待实现功能（按优先级）

### 1. 发现机制（Discovery）- 高优先级 ✅ 已完成
- [x] ContractPool/Registry（合约池）
  - [x] 扫描系统 declaration 文件（data_keys/*/declaration.py）
  - [x] 建立 data_key → declaration 映射（18个）
  - [x] 加载 loader（从 declaration）
- [x] 发现 API
  - [x] get_contract(data_key) → Contract 实例
  - [x] list_available_data_keys() → 可用 data_key列表
  - [x] register_custom_declaration(declaration) → 注册自定义
- [x] 清理旧代码
  - [x] 删除所有 key.py（16个）
  - [x] 删除旧 discovery.py
  - [x] 更新所有 loader.py 导入路径
  - [x] 验证测试通过

### 2. 缓存管理（Cache）- 高优先级 ✅ 已完成
- [x] ContractCacheManager
  - [x] global/per-strategy两层缓存
  - [x] 生命周期管理（enter_strategy_run/exit_strategy_run）
  - [x] 缓存策略（自动缓存 global scope）
- [x] 缓存集成到 BaseDataKey
  - [x] fill_in_data检查缓存（仅 global scope）
  - [x] global scope数据自动缓存
  - [x] fingerprint计算（SHA256）
  - [x] force_reload参数（忽略缓存）

### 3. 数据注入管理（Issue Manager）- 中优先级
- [ ] DataContractManager
  - [ ] mapping合并（system + user）
  - [ ] issue/load API
  - [ ] 批量contract管理
- [ ] Facade API（contracts.py）
  - [ ] issue(data_key, runtime) → Contract
  - [ ] load(contract) → 数据
  - [ ] batch_load(contracts) → 批量加载

### 4. 时间辅助工具（Time Helpers）- 低优先级
- [ ] ContractTimeHelper
  - [ ] time_axis_field/format获取
  - [ ] 时间格式转换（YYYYMMDD/YYYY-MM-DD/YYYYQ）
  - [ ] normalize_as_of（时间标准化）

### 5. 数据生命周期管理（Lifecycle）- 低优先级
- [ ] merge（合并数据）
  - [ ] append-tail merge
  - [ ] 时间序列合并
- [ ] drop（删除数据）
  - [ ] drop_before（释放内存）
- [ ] extend（扩展数据）
  - [ ] 动态加载新数据

### 6. 数据验证（Validation）- 低优先级
- [ ] validate_raw（原始数据验证）
- [ ] validate_declaration（声明完整性检查）

### 7. 其他优化
- [ ] ContractMeta添加更多字段（attrs等）
- [ ] 支持context参数（loader上下文）
- [ ] 错误处理和日志

## 当前任务
**已完成：清理旧代码**
- [x] 批量创建16个 declaration.py
- [x] 批量删除所有 key.py
- [x] 更新所有 loader.py 导入路径
- [x] 更新所有 __init__.py
- [ ] 删除旧的 discovery.py
- [ ] 验证新的发现机制工作

## 下一步
**开始实现：缓存管理（Cache）**
- 实现 ContractCacheManager
- 集成缓存到 BaseDataKey
- 实现时间辅助工具