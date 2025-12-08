# Data Source 渐进式重构计划

## 背景

data_source 是项目中最复杂的部分之一，现有实现包含：
- 多线程/多进程数据获取
- 进度跟踪（ProgressTracker）
- 限流器（RateLimiter）
- 错误重试和容错
- 数据验证和清洗
- 增量更新逻辑
- 依赖关系管理

**决策：** 采用渐进式重构，保留现有功能，逐步演进到新架构。

---

## 重构目标

### 新架构特点

1. **统一接口**：BaseProvider 定义标准 API
2. **动态挂载**：ProviderRegistry 支持插件化
3. **协调层**：DataCoordinator 处理复杂依赖
4. **适配器模式**：包装现有实现，保留所有功能

### 核心原则

- ✅ **渐进式**：不影响现有功能
- ✅ **向后兼容**：可切换新旧架构
- ✅ **功能保留**：保留所有复杂功能
- ✅ **按需迁移**：逐步替换，不强制

---

## 架构演进

### 当前架构（Legacy）

```
DataSourceManager
    ├── Tushare (providers/tushare/main.py)
    │   ├── RateLimiter
    │   ├── ProgressTracker
    │   └── Renewers (stock_kline, corporate_finance, etc.)
    └── AKShare (providers/akshare/main.py)
        └── Renewers
```

### 目标架构（V2）

```
DataSourceManager
    ├── ProviderRegistry
    │   ├── TushareProvider
    │   └── AKShareProvider
    └── DataCoordinator
        ├── 自动路由
        ├── 依赖处理
        └── 降级策略
```

### 过渡架构（Adapters）

```
DataSourceManager (支持新旧切换)
    ├── Legacy Mode (默认)
    │   └── 使用现有 providers/tushare, providers/akshare
    │
    └── V2 Mode (可选)
        ├── TushareAdapter → 包装 legacy/Tushare
        └── AKShareAdapter → 包装 legacy/AKShare
```

---

## 目录结构

```
app/data_source/
├── DESIGN.md                      # 新架构设计
├── MIGRATION.md                   # 本文档
│
├── legacy/                        # 旧架构（完整保留）
│   ├── data_source_manager.py
│   └── providers/
│       ├── tushare/
│       │   ├── main.py            # 保留所有功能
│       │   ├── renewers/
│       │   ├── rate_limiter.py
│       │   └── base_renewer.py
│       └── akshare/
│           └── ...
│
├── v2/                            # 新架构
│   ├── base_provider.py           # 统一接口
│   ├── provider_registry.py       # 动态挂载
│   ├── data_coordinator.py        # 协调层
│   ├── adapters/                  # 适配器（关键）
│   │   ├── tushare_adapter.py     # 包装旧 Tushare
│   │   └── akshare_adapter.py     # 包装旧 AKShare
│   └── providers/                 # 新实现（未来）
│
├── data_source_manager.py         # 统一管理器（兼容新旧）
└── enums.py
```

---

## 迁移计划

### Phase 1: 基础设施（1-2天）

**目标：** 创建新架构骨架

**任务：**
- [x] 创建 `v2/` 目录
- [ ] 实现 `BaseProvider` 接口
  ```python
  class BaseProvider(ABC):
      @abstractmethod
      def fetch(self, request: DataRequest) -> DataResponse
      @abstractmethod
      def supports(self, data_type: str) -> bool
  ```
- [ ] 实现 `ProviderRegistry`（动态挂载）
- [ ] 实现 `DataCoordinator`（协调层）
- [ ] 编写 `DESIGN.md`

**验收标准：**
- 新架构代码可运行
- 不影响现有功能
- 单元测试通过

---

### Phase 2: 适配器（2-3天）

**目标：** 通过适配器包装旧实现

**任务：**
- [ ] 实现 `TushareAdapter`
  - 包装 `legacy/providers/tushare/main.py`
  - 保留多线程功能
  - 保留进度跟踪
  - 保留限流器
  - 保留错误重试
- [ ] 实现 `AKShareAdapter`
  - 包装 `legacy/providers/akshare/main.py`
  - 保留所有现有功能
- [ ] 单元测试
  - 对比新旧输出一致性
  - 性能测试

**验收标准：**
- 适配器功能与旧实现一致
- 所有测试通过
- 性能无明显下降

---

### Phase 3: 可选切换（1天）

**目标：** 支持通过配置切换新旧架构

**任务：**
- [ ] 更新 `DataSourceManager`
  ```python
  def __init__(self, data_manager, use_v2: bool = False):
      if use_v2:
          self._init_v2()  # 使用新架构（适配器）
      else:
          self._init_legacy()  # 使用旧架构（默认）
  ```
- [ ] 在 `start.py` 中添加配置
  ```bash
  python start.py renew --use-v2  # 使用新架构
  python start.py renew           # 使用旧架构（默认）
  ```
- [ ] 集成测试

**验收标准：**
- 可以通过参数切换
- 两种模式结果一致
- 默认使用旧架构（安全）

---

### Phase 4: 逐步替换（按需）

**目标：** 用新实现替换适配器

**策略：** 从简单到复杂

**优先级：**
1. **简单数据类型**（独立、无依赖）
   - GDP（宏观经济）
   - CPI/PPI（价格指数）
   - Shibor/LPR（利率）
   
2. **中等复杂度**（有依赖但清晰）
   - 股票列表
   - 股票标签
   
3. **复杂数据类型**（最后）
   - K线数据（多线程、大批量）
   - 企业财务（复杂依赖）
   - 复权因子（依赖K线）

**每个数据类型的迁移步骤：**
1. 在 `v2/providers/` 创建新实现
2. 编写单元测试
3. 性能对比（与旧实现）
4. 更新适配器使用新实现
5. 集成测试
6. 文档更新

---

### Phase 5: 清理（未来）

**目标：** 完全迁移到新架构

**条件：**
- 所有数据类型已迁移
- 新架构运行稳定（至少6个月）
- 性能满足要求
- 所有测试通过

**任务：**
- [ ] 删除 `legacy/` 目录
- [ ] 移除 `use_v2` 参数（新架构成为默认）
- [ ] 更新所有文档
- [ ] 发布 v2.0

---

## 保留的功能清单

所有现有功能都必须在新架构中保留：

### 1. 多线程/多进程
- **位置：** `legacy/providers/tushare/main.py`
- **实现：** 使用 `FuturesWorker`
- **保留方式：** 适配器直接调用旧实现

### 2. 进度跟踪
- **位置：** `utils/progress/progress_tracker.py`
- **功能：** 显示更新进度、ETA
- **保留方式：** 适配器继承

### 3. 限流器
- **位置：** `legacy/providers/tushare/rate_limiter.py`
- **功能：** API 调用限流、令牌桶算法
- **保留方式：** 适配器继承

### 4. 错误重试
- **位置：** `legacy/providers/tushare/base_renewer.py`
- **功能：** 自动重试、指数退避
- **保留方式：** 适配器继承

### 5. 增量更新
- **位置：** 各个 renewer
- **功能：** 只更新缺失的数据
- **保留方式：** 适配器继承

### 6. 数据验证
- **位置：** 各个 renewer
- **功能：** 数据格式验证、清洗
- **保留方式：** 适配器继承

---

## 风险控制

### 风险1：功能丢失
- **措施：** 单元测试对比新旧输出
- **验证：** 集成测试覆盖所有场景

### 风险2：性能下降
- **措施：** 适配器只是薄包装，不改逻辑
- **验证：** 性能测试

### 风险3：引入新 Bug
- **措施：** 默认使用旧架构，新架构可选
- **回滚：** 随时可切换回旧架构

---

## 时间估算

| 阶段 | 任务 | 预计时间 | 状态 |
|-----|------|---------|------|
| Phase 1 | 基础设施 | 1-2天 | ⏳ 待开始 |
| Phase 2 | 适配器 | 2-3天 | ⏳ 待开始 |
| Phase 3 | 可选切换 | 1天 | ⏳ 待开始 |
| Phase 4 | 逐步替换 | 按需 | ⏳ 待开始 |
| Phase 5 | 清理 | 未来 | ⏳ 待开始 |

**总计：** 4-6天（基础架构） + 按需迁移

---

## 成功标准

### 短期（Phase 1-3 完成后）
- ✅ 新架构可用
- ✅ 可选切换（`use_v2=True`）
- ✅ 功能完全一致
- ✅ 性能无明显下降

### 中期（部分迁移后）
- ✅ 至少2个数据类型用新实现
- ✅ 新架构稳定运行
- ✅ 文档完善

### 长期（完全迁移后）
- ✅ 所有数据类型迁移
- ✅ 删除 legacy 代码
- ✅ 新架构成为默认
- ✅ 易于添加新 Provider

---

## 参考资料

- [DESIGN.md](./DESIGN.md) - 新架构设计文档
- [Legacy Tushare](./legacy/providers/tushare/main.py) - 旧实现参考

---

**最后更新：** 2025-12-05  
**维护者：** @garnet

