## 变更日志（Changelog）

本文件汇总 New Tea Quant 的主要版本变更。  
自 `v0.1.0` 起采用统一版本规范 `v[a].[b].[c]`（a=Version，b=Function，c=Patch）。  
`v0.0.x` 段为对历史内部里程碑（原文档中的 v2/v3/v4）的回溯编号。

---

### v0.2.2 (2026-04-21)

- 增加了Readme里的小徽章和相应的github gitee自动化
- 添加英文Readme
- 增加了UT coverage和merge的最小要求
- 对所有模块增加了测试的覆盖率，修复Github的CI错误
- 为官网增加了不少新的样式
- 在官网重新写了API文档，对NTQ的死链接进行了清理
- 修复了官网注册不成功的bug，修改了官网提交反馈form的时候会出现email无法发送的bug

---

---

### v0.2.1 (2026-04-14)

- 为所有模块设计并添加了info的信息，并增加了对核心的版本支持能力
- 废弃并删除了core/data_class
- 重构所有文档的位置和内容，让文档保持最新状态
- 重构userspace里的用户readme文档，让概念和例子更加易懂
- 定义了文档标准并记录在`docs/module-doc-standard.md`
- cli增加显示版本信息的命令`python start-cli --verison`

---

### v0.2.0 (2026-04-13)

- 新增加了data contract的核心模块，为核心策略和标签模块增加了用户可扩展的数据契约
- 制作了一个最小demo合集，让用户5分钟能跑起来框架
- 在tag和strategy里集成了data contract模块
- 去掉了tag模块写死的多进程分配逻辑，变成可自动通过内存变化分配进程的auto模式
- 增加了所有相关UT

---


---

### v0.1.1 (2026-04-05)

- 修复了数据库配置中配置需要mysql：或者 postgresql：包裹的bug，更新了db的example的配置文件
- 更新了所有的UT，增加coverage，更新了README里的运行pytest的部分

---


---

### v0.1.0 (2026-02-11)

- 首个对外开源的预发布版本；
- 统一许可证为 Apache License 2.0，并清理文档中与之冲突的非商业条款；
- 清理硬编码的本地路径和个人 workspace 配置，完善 Tushare token 等配置指引；
- 新增开源配套文档：`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`、`SUPPORT.md`、`.github` issue/PR 模板；
- 新增基础 CI（GitHub Actions）流水线与测试说明；
- 在 README 中补充项目定位、版本规范说明以及公共 API / 内部实现的边界说明。

---

### v0.0.3 (2026-01-15)

- 🎯 **三层回测架构**：机会枚举 → 价格因子模拟 → 资金分配模拟；
- 💰 **资金分配模拟器**：真实资金约束下的组合回测，支持等资金/等股/Kelly 分配策略；
- 📉 **价格因子模拟器**：无资金约束的信号质量评估，快速验证策略有效性；
- 🏷️ **版本管理系统**：独立的版本控制，支持多轮回测结果对比；
- ⚙️ **配置系统重构**：统一的配置结构，移除向后兼容，更清晰的字段命名；
- 🔄 **模块化优化**：代码拆分和重构，提高可维护性；
- 📊 **结果输出优化**：详细的交易记录、权益曲线、汇总统计；
- 🗄️ **DataManager 重构**：Facade + Service 架构，职责分离，明确性优先；
- 📦 **DataSource 系统**：Handler + Provider 架构，配置驱动、易于扩展，支持多数据源切换；
- 🏷️ **Tag 系统**：Scenario + Tag 三层架构，配置驱动的标签计算框架，支持多进程并行计算；
- 📈 **Indicator 模块**：基于 `pandas-ta-classic`，支持 150+ 技术指标，通用模块设计；
- 🔧 **Infrastructure 完善**：Database 和 Worker 系统优化，多进程安全，自动资源管理。

---

### v0.0.2 (2024-09-25)

- 重构策略框架，支持插件化策略；
- 新增投资目标管理系统；
- 新增自定义结算逻辑支持；
- 新增 Momentum、MeanReversion 策略；
- 优化 RTB 策略（ML 增强版）；
- 完善文档和示例。

---

### v0.0.1 (2024-07-26)

- 从 Node.js 迁移到 Python；
- 重构系统架构；
- 添加多数据源支持。

