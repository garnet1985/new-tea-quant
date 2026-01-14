# DuckDB 所有数据库写入操作审计

## 🔍 审计目标

检查所有数据库写入操作，确保多进程/多线程场景下的写入都通过批量写入队列，避免并发写入冲突。

---

## ✅ 已通过 queue_write 的写入（自动支持批量写入队列）

### 1. 通过 `model.replace()` 的写入
**路径**：`DbBaseModel.replace()` → `db.queue_write()`

**已支持的模块**：
- ✅ **KlineHandler** - `after_single_task_execute` / `after_all_tasks_execute`
- ✅ **CorporateFinanceHandler** - `after_single_task_execute`
- ✅ **AdjFactorEventHandler** - `after_single_task_execute`
- ✅ **RollingHandler** - `after_normalize`
- ✅ **PriceIndexesHandler** - `after_normalize`
- ✅ **StockIndexIndicatorHandler** - `after_normalize`
- ✅ **StockIndexIndicatorWeightHandler** - `after_normalize`
- ✅ **TagValueModel.batch_save_tag_values()** - 多进程 tag 计算后保存
- ✅ **TagDefinitionModel.save_tag_definition()** - tag 元信息保存
- ✅ **InvestmentDataService.save_trade()** (使用 replace 时)

---

## ⚠️ 需要检查的写入操作

### 1. `DbBaseModel.insert()` - 直接使用 `cursor.executemany()`

**文件**：`app/core/infra/db/db_base_model.py:600`

**问题**：
- 直接使用 `cursor.executemany()`，**没有走 `queue_write()`**
- 在多进程/多线程场景下可能导致写锁冲突

**使用场景**：
- `InvestmentDataService.save_trade()` (没有 id 时)
- `InvestmentDataService.save_operation()`
- `InvestmentDataService.save_operations_batch()`
- `InvestmentOperationsModel.save_operations()`

**影响**：
- ⚠️ **Investment 写入**：如果多个进程/线程同时保存 investment 数据，会有写锁冲突
- ⚠️ **Tag 写入**：虽然 tag value 使用 `replace()`，但如果有其他使用 `insert()` 的场景，也会有冲突

**解决方案**：
- 修改 `insert()` 方法，使其也使用 `queue_write()`
- 或者为 `insert()` 添加批量写入队列支持

---

### 2. `DbBaseModel.update()` - 直接使用 `cursor.execute()`

**文件**：`app/core/infra/db/db_base_model.py:625`

**问题**：
- 直接使用 `cursor.execute()`，**没有走 `queue_write()`**
- 在多进程/多线程场景下可能导致写锁冲突

**使用场景**：
- `TagScenarioModel.update()` - 更新 scenario 状态
- `TagDefinitionModel.update()` (如果有)
- `MetaInfoModel.update()` - 更新元信息

**影响**：
- ⚠️ **Tag Scenario 更新**：如果多个进程同时更新 scenario，会有写锁冲突
- ⚠️ **MetaInfo 更新**：如果多个进程同时更新元信息，会有写锁冲突

**解决方案**：
- 修改 `update()` 方法，使其也使用 `queue_write()`
- 或者为 `update()` 添加批量写入队列支持

---

### 3. `TagService.batch_update_tag_definitions()` - 直接使用 `cursor.execute()`

**文件**：`app/core/modules/data_manager/data_services/stock/sub_services/tag_service.py:315`

**问题**：
- 直接使用 `cursor.execute()` 执行 UPDATE，**没有走 `queue_write()`**
- 在多进程/多线程场景下可能导致写锁冲突

**使用场景**：
- 批量更新 tag definitions（通常在主进程执行，但需要确认）

**影响**：
- ⚠️ **Tag Definition 批量更新**：如果多个进程同时更新，会有写锁冲突

**解决方案**：
- 改为使用 `model.update()` 或 `queue_write()`
- 或者确保只在单进程场景下使用

---

### 4. `DbBaseModel.execute_raw_update()` - 直接使用 `cursor.execute()`

**文件**：`app/core/infra/db/db_base_model.py:853`

**问题**：
- 直接使用 `cursor.execute()`，**没有走 `queue_write()`**

**使用场景**：
- 执行原始 SQL UPDATE 语句（使用较少）

**影响**：
- ⚠️ **原始 SQL 更新**：如果多个进程同时执行，会有写锁冲突

**解决方案**：
- 添加警告，建议使用 `queue_write()` 或 `replace()`
- 或者确保只在单进程场景下使用

---

## 📊 写入操作分类

### 按写入方法分类

| 写入方法 | 是否走 queue_write | 多进程/多线程安全 | 需要修改 |
|---------|-------------------|-----------------|---------|
| `model.replace()` | ✅ 是 | ✅ 安全 | ❌ 无需修改 |
| `model.insert()` | ❌ 否 | ❌ 不安全 | ✅ **需要修改** |
| `model.update()` | ❌ 否 | ❌ 不安全 | ✅ **需要修改** |
| `cursor.execute()` | ❌ 否 | ❌ 不安全 | ✅ **需要检查** |
| `cursor.executemany()` | ❌ 否 | ❌ 不安全 | ✅ **需要检查** |

### 按使用场景分类

| 场景 | 写入方法 | 是否多进程/多线程 | 是否安全 | 优先级 |
|------|---------|-----------------|---------|-------|
| **Tag Value 保存** | `replace()` | ✅ 多进程 | ✅ 安全 | - |
| **Tag Definition 保存** | `replace()` | ✅ 多进程 | ✅ 安全 | - |
| **Tag Scenario 更新** | `update()` | ❓ 待确认 | ❌ 不安全 | 🔴 高 |
| **Investment Trade 保存** | `insert()` / `replace()` | ❓ 待确认 | ❌ 不安全 | 🔴 高 |
| **Investment Operation 保存** | `insert()` | ❓ 待确认 | ❌ 不安全 | 🔴 高 |
| **Tag Definition 批量更新** | `cursor.execute()` | ❓ 待确认 | ❌ 不安全 | 🟡 中 |
| **MetaInfo 更新** | `update()` | ❓ 待确认 | ❌ 不安全 | 🟡 中 |

---

## 🎯 修改优先级

### 🔴 高优先级（立即修改）

1. **修改 `DbBaseModel.insert()`**
   - 改为使用 `queue_write()` 或添加批量写入队列支持
   - 影响：Investment 写入、所有使用 `insert()` 的场景

2. **修改 `DbBaseModel.update()`**
   - 改为使用 `queue_write()` 或添加批量写入队列支持
   - 影响：Tag Scenario 更新、MetaInfo 更新

### 🟡 中优先级（本周完成）

3. **检查 `TagService.batch_update_tag_definitions()`**
   - 确认是否在多进程场景下使用
   - 如果是，改为使用 `queue_write()` 或确保单进程执行

4. **检查所有使用 `cursor.execute()` 的地方**
   - 确认是否在多进程/多线程场景下使用
   - 如果是，改为使用 `queue_write()` 或确保单进程执行

### 🟢 低优先级（可选）

5. **添加写入方法使用指南**
   - 文档说明哪些方法在多进程/多线程场景下安全
   - 添加警告和最佳实践

---

## 📝 详细修改计划

### TODO-1: 修改 `DbBaseModel.insert()` 使用批量写入队列

**文件**：`app/core/infra/db/db_base_model.py`

**当前实现**：
```python
def insert(self, data_list: List[Dict[str, Any]]) -> int:
    # 直接使用 cursor.executemany()
    with self.db.get_sync_cursor() as cursor:
        cursor.executemany(query, values)
```

**修改方案**：
- 方案 A：改为使用 `queue_write()`（推荐）
- 方案 B：为 `insert()` 添加批量写入队列支持（需要定义 unique_keys）

**推荐方案 A**：
```python
def insert(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
    """批量插入数据（使用批量写入队列）"""
    if not data_list:
        return 0
    
    # 如果有 unique_keys，使用 replace（支持去重）
    if unique_keys:
        return self.replace(data_list, unique_keys)
    
    # 否则使用 queue_write（但需要定义 unique_keys）
    # 或者直接写入（单进程场景）
    # TODO: 需要确认 insert 是否应该支持去重
```

**问题**：
- `insert()` 通常不需要去重（与 `replace()` 的区别）
- 但批量写入队列需要 `unique_keys` 来构建 ON CONFLICT 语句
- **解决方案**：如果 `unique_keys` 为空，使用 `INSERT INTO ... VALUES ...`（不处理冲突）

---

### TODO-2: 修改 `DbBaseModel.update()` 使用批量写入队列

**文件**：`app/core/infra/db/db_base_model.py`

**当前实现**：
```python
def update(self, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
    # 直接使用 cursor.execute()
    with self.db.get_sync_cursor() as cursor:
        cursor.execute(query, tuple(data.values()) + params)
```

**修改方案**：
- UPDATE 语句比较复杂，需要 WHERE 条件
- 批量写入队列主要处理 INSERT ... ON CONFLICT，不太适合 UPDATE
- **解决方案**：UPDATE 操作通常在主进程执行，可以保持现状，但需要添加警告

**或者**：
- 为 UPDATE 操作添加队列支持（需要重新设计批量写入队列）

---

### TODO-3: 检查 Tag 多进程写入

**确认点**：
- [ ] Tag 计算是否在多进程中执行？
- [ ] 每个进程是否独立保存 tag values？
- [ ] Tag scenario 更新是否在多进程中执行？

**当前状态**：
- ✅ Tag value 保存使用 `replace()`，已支持批量写入队列
- ⚠️ Tag scenario 更新使用 `update()`，需要检查

---

### TODO-4: 检查 Investment 多进程写入

**确认点**：
- [ ] Investment 数据保存是否在多进程/多线程场景下执行？
- [ ] 如果是，需要修改 `insert()` 方法

**当前状态**：
- ⚠️ Investment trade 保存使用 `insert()` 或 `replace()`
- ⚠️ Investment operation 保存使用 `insert()`

---

## 🔗 相关文件

- [批量写入队列实现](./app/core/infra/db/batch_write_queue.py)
- [数据库管理器](./app/core/infra/db/db_manager.py)
- [数据库基础模型](./app/core/infra/db/db_base_model.py)
- [TODO 清单](./DUCKDB_CONCURRENT_WRITE_TODO.md)
