# Data Source 重要决策记录

**版本：** 3.0  
**最后更新**: 2026-01-23

---

本文档记录了 Data Source 模块的重要架构设计决策，包括问题背景、可选方案、决策理由和影响。

---

## 决策 1：三层架构设计

**日期**：2025-12-19  
**状态**：已实施

### 痛点

在重构数据源模块之前，存在以下问题：
- 硬编码的数据获取逻辑：每个数据源的获取逻辑都硬编码在 `DataSourceManager` 中，难以扩展和维护
- 职责不清：Provider、Handler、Manager 的职责边界模糊
- API 限流管理混乱：限流逻辑分散在各个 handler 中，难以统一管理
- 难以切换数据源：要切换数据源（如从 Tushare 切换到 AKShare），需要修改代码

### 可选方案

**方案 A：单层架构（所有逻辑在一个类中）**
- 优点：简单直接
- 缺点：职责不清，难以维护，代码臃肿

**方案 B：两层架构（Manager + Handler）**
- 优点：职责分离，易于理解
- 缺点：Provider 和 Handler 职责不清，难以管理

**方案 C：三层架构（Manager + Handler + Provider）** ✅
- 优点：职责清晰，易于扩展，支持灵活切换
- 缺点：层级稍多，学习成本略高

### 为什么选择当前方案

选择方案 C（三层架构）的理由：
1. **职责清晰**：Manager 负责协调管理，Handler 负责业务逻辑，Provider 负责 API 封装
2. **易于扩展**：添加新的 Provider 或 Handler 只需在对应层级实现，不影响其他层级
3. **灵活切换**：通过配置切换 Provider，无需修改代码
4. **符合设计原则**：遵循单一职责原则和开闭原则

### 架构设计细节

**1. Provider 层（基础设施）**
- **职责**：纯 API 封装，认证配置，API 元数据声明，错误转换
- **不负责**：业务逻辑，数据标准化，限流执行，多线程调度

**2. Handler 层（业务逻辑）**
- **职责**：数据获取逻辑，数据标准化，多 Provider 组合，依赖处理
- **不负责**：多线程调度，全局限流管理

**3. Manager 层（协调管理）**
- **职责**：配置加载和 Handler 注册，全局依赖解析和注入，运行所有启用的 handler
- **不负责**：具体的数据获取逻辑，数据标准化逻辑，依赖处理，限流执行

### 影响

- 代码结构清晰，易于理解和维护
- 新 Provider 或 Handler 添加简单，只需在对应层级实现
- 可以灵活切换 Provider，无需修改代码
- 职责边界清晰，便于测试和维护

---

## 决策 2：依赖注入架构

**日期**：2025-12-19  
**状态**：已实施

### 痛点

在早期设计中，`latest_completed_trading_date` 和 `stock_list` 在多个 handler 中重复获取，导致：
- 数据不一致：不同 handler 可能获取到不同版本的依赖数据
- 性能问题：重复获取相同的依赖数据，浪费资源
- 代码重复：每个 handler 都需要实现相同的依赖获取逻辑

### 可选方案

**方案 A：每个 Handler 自己获取依赖**
- 优点：实现简单
- 缺点：数据不一致，性能问题，代码重复

**方案 B：统一依赖管理，在 renew_data 开始时统一获取** ✅
- 优点：数据一致，性能好，代码简洁
- 缺点：需要设计依赖注入机制

### 为什么选择当前方案

选择方案 B 的理由：
1. **统一依赖管理**：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
2. **按需获取**：只获取真正需要的依赖，避免不必要的开销
3. **配置驱动**：通过 `mapping.json` 显式声明每个 handler 的依赖需求
4. **易于扩展**：预留接口，方便未来添加新的全局依赖
5. **状态隔离**：context 只在 `renew_data` 方法内存在，方法执行完自动销毁

### 依赖声明规则

1. **显式声明**：每个 handler 必须显式声明所有依赖（即使为 `false`）
2. **布尔值**：`true` 表示需要，`false` 表示不需要
3. **默认值**：如果某个 handler 没有 `dependencies` 字段，默认所有依赖都为 `false`

### 影响

- 所有 handler 使用一致的全局依赖，确保数据一致性
- 减少重复获取，提高性能
- 配置驱动，易于维护和扩展
- context 状态隔离，避免状态污染

---

## 决策 3：HandlerConfig 设计

**日期**：2026-01-17  
**状态**：已实施

### 痛点

在早期设计中，存在以下问题：
1. **配置职责混乱**：`mapping.json` 中同时包含 data source 到 handler 的映射配置和 handler 的业务配置
2. **HandlerConfig 类设计困惑**：需要明确哪些配置类应该在 `core` 中，哪些应该在 `userspace` 中
3. **学习成本问题**：需要平衡类型精确性和学习成本

### 可选方案

**方案 A：一个基类（BaseHandlerConfig）** ✅
- 优点：学习成本最低，简单直接，灵活性高
- 缺点：所有 Handler 看到所有选项（可以通过文档说明）

**方案 B：多个配置类（BaseHandlerConfig、RollingHandlerConfig、SimpleApiHandlerConfig）**
- 优点：类型精确，每个 Handler 只看到相关选项
- 缺点：学习成本高，需要理解复杂的自动选择逻辑、配置冲突检测

### 为什么选择当前方案

选择方案 A 的理由：
1. **学习成本最低**：用户只需要知道 `BaseHandlerConfig`
2. **简单直接**：不需要理解复杂的自动选择逻辑、配置冲突检测
3. **灵活性**：所有选项都在一个基类中，用户可以根据需要选择使用
4. **缺点可以接受**：所有 Handler 看到所有选项可以通过文档说明

### 设计原则

1. **所有选项都在 BaseHandlerConfig 中**：基础选项 + rolling 选项 + simple_api 选项
2. **Config 类是可选的**：如果用户定义了 Config 类，使用 Config 类的默认值；如果没有，直接使用 `mapping.json` 中的字典
3. **两种配置的职责分离**：Handler 默认配置（JSON 文件）和 mapping 配置（覆盖默认值）
4. **配置读取顺序**：JSON 配置文件 → Config 类默认值 → mapping.json → get_param 的 default 参数

### 影响

- 配置系统简单易用，学习成本低
- 支持灵活的配置方式（JSON 文件、Config 类、mapping.json）
- 所有 Handler 看到所有选项，但可以通过文档说明哪些选项适用于哪些场景

---

## 决策 4：Renew Mode 设计

**日期**：2026-01-XX  
**状态**：已实施

### 痛点

不同数据源有不同的数据更新需求：
- **增量更新**：只获取最新数据（从数据库最新日期到当前日期）
- **滚动更新**：获取最近 N 个时间单位的数据（如最近 4 个季度）
- **全量刷新**：获取指定日期范围内的所有数据

如果每个 Handler 都自己实现这些逻辑，会导致：
- 代码重复：相同的日期计算逻辑在多个 Handler 中重复
- 维护困难：修改日期计算逻辑需要修改多个 Handler
- 容易出错：每个实现可能有细微差异

### 可选方案

**方案 A：每个 Handler 自己实现日期计算逻辑**
- 优点：灵活性高
- 缺点：代码重复，维护困难，容易出错

**方案 B：使用 RenewModeService 统一处理** ✅
- 优点：代码复用，易于扩展，职责清晰
- 缺点：需要设计 Service 接口

### 为什么选择当前方案

选择方案 B 的理由：
1. **代码复用**：公共逻辑集中在 Service 中，所有 Handler 复用
2. **易于扩展**：添加新的 renew mode 只需实现新的 Service
3. **职责清晰**：Handler 专注于业务逻辑，日期计算由 Service 负责
4. **统一接口**：所有 Handler 使用统一的 `renew_mode` 配置

### 实现方案

- 使用 `RenewModeService` 作为统一入口
- 根据 `renew_mode` 路由到对应的 Service（`IncrementalRenewService`、`RollingRenewService`、`RefreshRenewService`）
- Handler 只需配置 `renew_mode` 和相关参数，框架自动处理日期范围计算

### 影响

- Handler 实现更简单，只需关注业务逻辑
- 日期计算逻辑统一维护，行为一致
- 新功能可以在 Service 中添加，所有 Handler 自动获得

---

## 决策 5：限流设计

**日期**：2026-01-XX  
**状态**：已实施

### 痛点

在早期设计中，限流逻辑分散在各个 handler 中，导致：
- 限流管理混乱：每个 handler 都有自己的限流逻辑，难以统一管理
- 线程安全问题：多线程环境下限流逻辑可能失效
- 窗口边界突刺：固定窗口限流在窗口切换时可能出现突刺

### 可选方案

**方案 A：每个 Handler 自己实现限流**
- 优点：灵活性高
- 缺点：限流管理混乱，线程安全问题，容易出错

**方案 B：Provider 声明限流信息，TaskExecutor 执行限流** ✅
- 优点：统一管理，线程安全，防止突刺
- 缺点：需要设计限流机制

### 为什么选择当前方案

选择方案 B 的理由：
1. **声明式**：Provider 只声明限流信息，不执行限流逻辑
2. **统一管理**：所有限流逻辑集中在 `TaskExecutor`
3. **线程安全**：使用锁和条件变量保证线程安全
4. **防止突刺**：窗口切换冷却机制，防止边界突刺

### 实现方案

- Provider 声明限流信息（`api_limits` 类属性）
- `TaskExecutor` 负责执行限流（通过 `RateLimiter`）
- 固定窗口限流，窗口对齐到自然分钟
- 窗口切换时强制冷却，防止边界突刺

### 影响

- 限流逻辑统一管理，易于维护
- 线程安全，支持多线程环境
- 防止窗口边界突刺，保证限流准确性

---

## 决策 6：Data Source 不负责数据存储

**日期**：2026-01-23  
**状态**：已实施

### 痛点

在早期设计中，部分 Handler 在数据标准化后直接保存数据，导致：
- **职责边界模糊**：Data Source 模块既负责数据获取，又负责数据存储，职责不清
- **复杂度增加**：如果 Data Source 管理 save，需要处理 Data Source Schema 和 DB Schema 的映射关系，增加系统复杂度
- **用户体验下降**：用户需要理解两套 Schema（Data Source Schema 和 DB Schema）的映射关系，学习成本高
- **灵活性受限**：统一的 save 机制难以满足不同业务场景的存储需求（如不同的存储时机、格式转换等）

### 可选方案

**方案 A：Data Source 默认提供 save 功能**
- 优点：用户使用方便，不需要自己实现 save
- 缺点：职责边界不清，需要处理 Schema 映射，复杂度高，灵活性差

**方案 B：Data Source 不负责存储，用户自行决定 save 时机和格式** ✅
- 优点：职责清晰，保持 Data Source 的纯粹性，灵活性高
- 缺点：用户需要在钩子中自行实现 save（但可以使用 data_manager）

### 为什么选择当前方案

选择方案 B 的理由：

1. **保持职责边界清晰**：
   - Data Source 的职责：数据获取和统一格式转换
   - Data Manager 的职责：数据入库和存储管理
   - 清晰的职责边界有助于系统的可维护性和可扩展性

2. **避免复杂度增加**：
   - Data Source Schema 和 DB Schema 可能不一致，需要映射
   - 如果 Data Source 管理 save，需要内置 Schema 映射逻辑
   - 这会导致 Data Source 模块复杂度显著增加，无论是实现复杂度还是用户体验都会变差

3. **提供灵活性**：
   - 用户可以在钩子函数（如 `on_after_normalize`）中自行决定 save 的时机
   - 用户可以根据业务需求选择不同的存储格式和策略
   - 用户可以使用 `data_manager` 提供的统一接口进行存储，保持一致性

4. **符合设计原则**：
   - 遵循单一职责原则：Data Source 专注于数据获取和格式转换
   - 遵循关注点分离：数据获取和存储分离，各司其职

### 设计原则

1. **Data Source 不默认带有 save 功能**：
   - `BaseHandler` 不提供默认的 save 方法
   - Handler 的生命周期钩子（如 `on_after_normalize`）只负责数据转换和处理，不负责存储

2. **用户可以在钩子中自行决定 save**：
   - 用户可以在 `on_after_normalize`、`on_after_execute_single_api_job` 等钩子中使用 `data_manager` 进行存储
   - 用户可以根据业务需求选择存储时机（如每个 API Job 完成后、所有数据标准化后等）
   - 用户可以根据业务需求进行格式转换后再存储

3. **使用 data_manager 进行存储**：
   - 虽然 Data Source 不负责 save，但用户可以在钩子中使用 `data_manager` 提供的统一接口
   - `data_manager` 负责处理 DB Schema 和存储逻辑
   - 这样既保持了职责边界，又提供了统一的存储接口

### 实现示例

```python
class MyHandler(BaseHandler):
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        # Data Source 的职责：数据转换和处理
        processed_data = self.process_data(normalized_data)
        
        # 用户自行决定存储时机和格式（使用 data_manager）
        data_manager = context.get("data_manager")
        if data_manager:
            # 可以根据业务需求进行格式转换
            db_records = self.convert_to_db_format(processed_data)
            # 使用 data_manager 进行存储
            data_manager.my_model.save_records(db_records)
        
        return processed_data
```

### 影响

- ✅ **职责边界清晰**：Data Source 专注于数据获取和格式转换，Data Manager 专注于数据存储
- ✅ **复杂度降低**：不需要处理 Data Source Schema 和 DB Schema 的映射关系
- ✅ **灵活性提高**：用户可以根据业务需求灵活决定存储时机和格式
- ✅ **用户体验改善**：用户只需要理解 Data Source Schema，不需要理解两套 Schema 的映射关系
- ⚠️ **需要用户自行实现 save**：用户需要在钩子中使用 `data_manager` 进行存储（但这是合理的，因为存储是业务逻辑的一部分）

---

## 相关文档

- **[overview.md](./overview.md)**：模块概览
- **[architecture.md](./architecture.md)**：架构文档

> **提示**：本文档记录了 Data Source 的重要设计决策。如需了解完整的架构设计，请参考 [architecture.md](./architecture.md)。

---

**文档结束**
