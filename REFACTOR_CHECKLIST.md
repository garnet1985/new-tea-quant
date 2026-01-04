# 引用更新清单

## 路径变更说明

### 主要变更
1. `app/core_modules/` → `app/core/modules/`
2. `app/data_manager/` → `app/core/modules/data_manager/`
3. `app/data_source/` → `app/core/modules/data_source/`
4. `app/tag/` → `app/core/modules/tag/`
5. `app/analyzer/` → `app/core/modules/analyzer/`
6. `utils/db/` → `app/core/infra/db/`
7. `utils/worker/` → `app/core/infra/worker/`
8. `utils/date/` → `app/core/utils/date/`
9. `utils/file/` → `app/core/utils/file/`
10. `utils/icon/` → `app/core/utils/icon/`
11. `utils/progress/` → `app/core/utils/progress/`
12. `app/core_modules/conf/` → `app/core/conf/`

---

## 模块清单

### 1. Data Manager 模块
**路径变更**: `app/core_modules/data_manager` → `app/core/modules/data_manager`

**需要更新的文件**:
- [x] `start.py` (1处) ✅
- [x] `app/core/modules/data_manager/data_manager.py` (多处) ✅
- [x] `app/core/modules/data_manager/__init__.py` (1处) ✅
- [x] `app/core/modules/data_manager/base_tables/__init__.py` (1处) ✅
- [x] `app/core/modules/data_manager/README.md` (1处) ✅
- [x] `app/core/modules/data_manager/base_tables/README.md` (1处) ✅
- [x] `app/core/modules/data_manager/base_tables/adj_factor_event/README.md` (2处) ✅
- [x] `app/core/modules/data_manager/data_services/README.md` (2处) ✅
- [x] `bff/api.py` (1处) ✅
- [x] `bff/APIs/stock_api.py` (1处) ✅
- [x] `bff/APIs/investment_api.py` (3处) ✅

**内部引用**:
- [x] `app/core/modules/data_manager/data_manager.py` 中的 `app.core_modules.conf.conf` → `app.core.conf.conf` ✅
- [x] `app/core/modules/data_manager/data_manager.py` 中的 `app.core_modules.analyzer` → `app.core.modules.analyzer` ✅

---

### 2. Data Source 模块
**路径变更**: `app/data_source` → `app/core/modules/data_source`

**需要更新的文件**:
- [ ] `start.py` (1处)
- [ ] `app/core/modules/data_source/data_source_manager.py` (3处)
- [ ] `app/core/modules/data_source/__init__.py` (5处)
- [ ] `app/core/modules/data_source/README.md` (2处)
- [ ] `app/core/modules/data_source/task_executor.py` (3处)
- [ ] `app/core/modules/data_source/providers/` 下所有文件 (多处)
- [ ] `app/core/modules/data_source/handlers/` 下所有文件 (多处)
- [ ] `app/core/modules/data_source/handlers/*/README.md` (多处)
- [ ] `app/userspace/data_source/README.md` (3处)
- [ ] `app/userspace/data_source/QUICK_START.md` (3处)
- [ ] `app/core/modules/data_manager/data_services/trading_date/trading_date_cache.py` (1处)

---

### 3. Tag 模块
**路径变更**: `app/core_modules/tag` → `app/core/modules/tag`

**需要更新的文件**:
- [ ] `start.py` (1处)
- [ ] `app/core/modules/tag/__init__.py` (4处)
- [ ] `app/core/modules/tag/core/tag_manager.py` (8处)
- [ ] `app/core/modules/tag/core/base_tag_worker.py` (4处)
- [ ] `app/core/modules/tag/core/models/scenario_model.py` (3处)
- [ ] `app/core/modules/tag/core/components/tag_worker_helper/tag_worker_data_manager.py` (1处)
- [ ] `app/core/modules/tag/core/components/helper/job_helper.py` (4处)
- [ ] `app/core/modules/tag/core/components/helper/tag_helper.py` (2处)
- [ ] `app/core/modules/tag/docs/DESIGN.md` (2处)
- [ ] `app/userspace/tags/momentum/settings.py` (1处)
- [ ] `app/userspace/tags/momentum/tag_worker.py` (2处)
- [ ] `app/userspace/tags/example_settings.py` (1处)

---

### 4. Analyzer 模块
**路径变更**: `app/analyzer` → `app/core/modules/analyzer`

**需要更新的文件**:
- [ ] `start.py` (1处)
- [ ] `app/core/modules/analyzer/components/__init__.py` (1处)
- [ ] `app/core/modules/analyzer/components/base_strategy.py` (多处)
- [ ] `app/core/modules/analyzer/components/simulator/services/preprocess_service.py` (2处)
- [ ] `app/core/modules/analyzer/components/simulator/services/simulating_service.py` (4处)
- [ ] `app/core/modules/analyzer/strategy/RTB/` 下所有文件 (多处)

---

### 5. Utils 模块迁移

#### 5.1 Database Utils
**路径变更**: `utils/db` → `app/core/infra/db`

**需要更新的文件**:
- [ ] `app/core/modules/data_manager/data_manager.py` (1处)
- [ ] `app/core/modules/data_manager/data_services/` 下多个文件 (多处)
- [ ] `app/core/modules/data_manager/base_tables/` 下所有 model.py (多处)
- [ ] `app/core/modules/data_source/handlers/` 下多个文件 (多处)
- [ ] `app/core/modules/analyzer/strategy/RTB/` 下多个文件 (多处)
- [ ] `app/core/infra/db/README.md` (多处)
- [ ] `app/core/modules/data_manager/base_tables/README.md` (1处)

#### 5.2 Worker Utils
**路径变更**: `utils/worker` → `app/core/infra/worker`

**需要更新的文件**:
- [x] `app/core/modules/analyzer/components/base_strategy.py` (1处) ✅
- [x] `app/core/modules/analyzer/components/simulator/services/simulating_service.py` (1处) ✅
- [x] `app/core/modules/tag/core/tag_manager.py` (2处) ✅
- [x] `app/core/modules/data_source/task_executor.py` (1处) ✅
- [x] `app/core/infra/worker/README.md` (多处) ✅
- [x] `app/core/infra/worker/multi_process/README.md` (1处) ✅
- [x] `app/core/infra/worker/multi_thread/README.md` (1处) ✅

#### 5.3 Date Utils
**路径变更**: `utils/date` → `app/core/utils/date`

**需要更新的文件**:
- [ ] `app/core/modules/data_manager/data_manager.py` (1处)
- [ ] `app/core/modules/data_manager/data_services/` 下多个文件 (多处)
- [ ] `app/core/modules/data_manager/base_tables/` 下多个文件 (多处)
- [ ] `app/core/modules/data_source/handlers/` 下多个文件 (多处)
- [ ] `app/core/modules/analyzer/components/` 下多个文件 (多处)
- [ ] `app/core/modules/tag/core/components/helper/job_helper.py` (1处)

#### 5.4 File Utils
**路径变更**: `utils/file` → `app/core/utils/file`

**需要更新的文件**:
- [ ] `app/core/modules/tag/core/components/helper/tag_helper.py` (1处)
- [ ] `app/core/utils/file/__init__.py` (1处 - 自引用)

#### 5.5 Icon Utils
**路径变更**: `utils/icon` → `app/core/utils/icon`

**需要更新的文件**:
- [ ] `app/core/modules/analyzer/components/` 下多个文件 (多处)
- [ ] `app/core/modules/analyzer/strategy/RTB/RTB.py` (1处)
- [ ] `app/core/modules/analyzer/strategy/HL/HL.py` (1处)

#### 5.6 Progress Utils
**路径变更**: `utils/progress` → `app/core/utils/progress`

**需要更新的文件**:
- [ ] `app/core/utils/progress/progress_tracker.py` (1处 - 自引用)

#### 5.7 Util (通用工具)
**路径变更**: `utils.util` → 保持不变（仍在根目录）

**需要更新的文件**:
- [ ] `app/core/modules/data_source/data_source_manager.py` (1处)

---

### 6. Conf 模块
**路径变更**: `app/core_modules/conf` → `app/core/conf`

**需要更新的文件**:
- [ ] `app/core/modules/data_manager/data_manager.py` (1处)
- [ ] `app/core/modules/tag/core/components/helper/job_helper.py` (1处)

---

## 统计

- **总文件数**: 约 80+ 个文件需要更新
- **总引用数**: 约 200+ 处引用需要更新

---

## 更新顺序建议

1. **Conf 模块** (最简单，只有2处)
2. **Utils 模块** (基础设施，影响面广)
   - Database Utils
   - Worker Utils
   - Date Utils
   - File Utils
   - Icon Utils
   - Progress Utils
3. **Data Manager 模块**
4. **Data Source 模块**
5. **Tag 模块**
6. **Analyzer 模块**
7. **BFF 模块**
8. **Start.py**

---

## 注意事项

1. 更新时注意区分：
   - `app.core.modules.xxx` (新路径)
   - `app.core_modules.xxx` (旧路径，需要替换)
   - `app.xxx` (可能是旧路径，需要检查)

2. 文档中的示例代码也需要更新

3. 某些文件可能有自引用，需要特别注意

4. 更新后需要验证导入是否正常
