## 变更日志（Changelog）

本文件汇总 New Tea Quant 的主要版本变更。  
自 `v0.1.0` 起采用统一版本规范 `v[a].[b].[c]`（a=Version，b=Function，c=Patch）。  
`v0.0.x` 段为对历史内部里程碑（原文档中的 v2/v3/v4）的回溯编号。

新版本更新清单：
python dev-cli -p -vx.x.x

[] (已自动化)同步 ``core/system.json`` 中的版本
[] (已自动化)同步版本徽章
[] (已自动化)确保所有test都能跑过
[] (已自动化)检查安装依赖的数据是不是齐全，是不是足够新
[] (已自动化)npm run build 产生UI资产
[] (已自动化)检查是不是有py3.9不支持的格式
[] 是否需要更新init data和init userspace，网站的数据和策略
[] 有破坏性更改或者新的模块需要在module_info.yaml里更新core的依赖
[] 检查是不是正确配置了gitignore
[] Changelog 里注明改动和可能存在的破坏性改动
[] 更新模块文档（模块readme，API，module_info）
[] 更新项目README文档

---

### v0.5.x (TBD)

目标，决策者模式
- 全线重命名capital allocation simulator成portfolio simulator
- 加入portfolio在选股时的决策函数

---


---

### v0.4.x (TBD)

目标，让整个项目的安装仅依赖python
- 系统支持parquet文件存储，使用duckDB进行调度，默认消除对第三方数据库的依赖
- 增加report里K线的点击界面
- 为新版本的更新增加清除缓存的步骤
- 给设置里增加清除缓存的功能
- import和export策略的支持

---


---

### v0.3.3 (2026-5-27)

- 重构获取股票列表的handler，获取全量股票列表，包括退市的
- 增加交易日历表和数据获取逻辑
- 增加风险时段表，记录每个股票的黑历史
- 资金回测过程中加入交易量限制，提高模拟准确性
- 重新打包了init_data里边包含回测期间已经退市的股票，清理老的数据表，减小对用户的认知负担
- 集成新表，数据和API进入回测系统，大幅减小幸存者偏差
- 优化了K线指标计算逻辑，指标计算速度提升65%以上
- 在dev-cli里加入自动检查python 3.9不支持语法的检查
- 在dev-cli加入数据打包功能（-ex）

---


---

### v0.3.2 (2026-5-20)
- 为非开发用户去除了Nodejs依赖
- 增加market profile模块，细化回测时候的交易规则
- 在userspace中提供了可以复写/添加新的market profile的配置
- 最小买入手数从100股变成了不同板块不同股数
- 加入涨停和跌停时限制交易的配置
- 根据不同股票或不同上市阶段，限制不同最大最小涨跌幅度
- 重新划分了project context模块的职责边界
- 新增加了一些UI样式：比如读取的动画，随机背景
- 优化UX，为很多地方添加了解释的tooltip。对次要内容使用tooltip进行归纳。最后增强了tooltip的视觉效果。
- 修复了核心设置的json发生变化就会导致整个设置区域消失的bug
- 在回测报告里加上了回测时间区间信息，并改进了枚举器关于时间的IO，大概提高6-8%的执行效率
- 为核心参数设置增加了大窗口编辑模式
- 优化了策略工作台执行步骤的进度显示
- 修复了工作台版本差异状态的变化显示错误
- UI header上的版本号改为从API获取

---


---

### v0.3.1 (2026-5-16)
- 将setup步骤变成UI版和命令行版本
- 修复了UI的npm安全性问题
- 修复了前端ESLint的警告
- 让UI端口使用python server，取消了使用者的Nodejs依赖（开发仍然需要）
- 增加了回测准确性的配置，可以配置交易终结价格以什么价格为主，从而更贴近现实交易回测
- 增加updater的一些基础功能，从0.4.x起，应该支持UI一键升级

---


---

### v0.3.0 (2026-05-11) - 此次版本更新将会引入破坏性改动

- 重大更新：UI系统发布，引入nodejs依赖
- 加入 `launcher.py`，一键启动 app 和 UI，自动发现安装状态并引导完成 Setup
- 在核心内加入BFF和UI，引入前端UI
- 完成策略工作台和策略扫描的UI和BFF
- 对齐UI和命令行的report，使输出结果保持一致
- 对命令行和UI的回测加入缓存系统，现在重复的回测会直接返回report
- 清理文件夹结构，将backup文件夹放入userspace，将docker以及badge生成还有自动更新readme这类代码放入devtools文件夹并更新代码引用和文档
- 收敛复权因子的逻辑进入model底层，并且为K线复权做了一条特殊快速通道，以便回测减小IO次数
- 在userspace里放入tables的文件夹，加入文档引导用户建立自己的数据表
- 重构strategy核心模块的组织方式，变成更直观的编排层 + flow流模式
- Strategy里加上了为支持输出的launcher和支持UI的adapter
- 扫描系统加入缓存，如果当日扫描过，将直接返回结果
- 清理start cli，变成代理层


破坏性改动：
- backup文件夹从更目录移动到了userspace
- app不再自带userspace文件夹，而是安装的时候自动创建
- start-cli 的扫描命令现在降级成一次只能用一个策略进行扫描
- 引入Nodejs依赖
- simulator的回测report格式发生了变化

---

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
- cli增加显示版本信息的命令`python start-cli --version`

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

