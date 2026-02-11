## 贡献指南

非常感谢你愿意为 `New Tea Quant` 做贡献！本指南帮助你快速搭建开发环境、理解基本流程，并以一致的方式提交改动。

---

### 环境准备

- **Python 版本**：建议使用 Python 3.9 及以上版本；
- **虚拟环境**：推荐使用 `venv`。

快速步骤（简化版，详细可参考 `docs/getting-started/installation.md` 和 `docs/getting-started/venv-usage.md`）：

```bash
git clone <repository-url>
cd new-tea-quant

python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

数据库和配置请参考：

- `docs/getting-started/configuration.md`
- 根目录 `README.md` 中的「快速开始」与「数据库配置」章节。

---

### 代码风格与规范

项目整体遵循以下约定（与 `README.md` 中「开发指南」一致）：

- **代码风格**：遵循 PEP 8；
- **类型注解**：鼓励使用 `typing` 进行类型标注；
- **日志**：使用标准库 `logging`，避免随意 `print`（除示例脚本或临时分析工具外）；
- **文档字符串**：对公共 API 编写清晰的 docstring；
- **最小化注释**：优先通过清晰命名与结构表达意图，只在有必要时补充注释。

提交信息建议使用类似规范：

```text
feat: 添加新功能
fix: 修复 bug
refactor: 代码重构
docs: 更新文档
chore: 构建工具或杂项变动
perf: 性能优化
test: 添加或更新测试
style: 代码格式调整（不影响逻辑）
```

---

### 如何提交改动

1. **Fork & 创建分支**
   - 从主仓库 Fork；
   - 基于 `main`（或当前默认分支）创建特性分支，例如 `feat/new-strategy-xxx`。

2. **保持提交小而清晰**
   - 每个提交尽量聚焦一个相对独立的改动；
   - 附带必要的文档/注释更新。

3. **运行基本检查**
   - 至少确保项目可以在本地正常导入与启动帮助：
     ```bash
     python start.py --help
     ```
   - 如你修改了某个子模块（例如 `core/modules/data_manager`），尽量编写或补充相应的测试/示例脚本。

4. **提交 Pull Request**
   - 清晰描述改动动机（Why）和主要内容（What）；
   - 关联相关的 issue（如有）；
   - 勾选 PR 模板中的检查项。

---

### 测试与质量保证

当前项目仍在活跃演进中，测试体系处于逐步完善阶段：

- 已有：以 `pytest` 为主的测试框架和部分核心模块测试（见 `docs/development/testing.md`）；
- 新增：基础 CI 流水线（GitHub Actions）会在 PR 和 main/master 分支上自动运行导入检查 + 可用的核心测试；
- 规划中：更系统的单元测试与端到端测试覆盖。

**如果你愿意贡献测试用例，非常欢迎：**

- 为新增/修改的模块补充单元测试；
- 为关键回测链路（机会枚举 → 价格因子模拟 → 资金分配模拟）补充集成测试；
- 在 PR 描述中说明如何在本地重现实验与验证步骤。

---

### 设计与架构讨论

框架有较为完整的架构文档，建议在进行较大改动前先阅读：

- `docs/architecture/project_overview.md`
- `docs/architecture/core_modules/*/architecture.md`
- `docs/architecture/infra/*/architecture.md`

如果你的改动会影响：

- 公共 API（对 `userspace/` 用户可见的接口）；
- 默认配置结构（`core/default_config` 与 `userspace/config` 的兼容性）；
- 数据库 Schema 或数据迁移逻辑；

请在 issue 或 PR 中明确说明，并优先发起设计讨论，避免破坏已有用户项目。

---

### 行为准则

本项目采用开源社区通用的行为准则，详情见：

- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

无论是 issue、PR 还是讨论区，都请保持尊重、友善与专业。

---

### 我可以做些什么？

如果你想参与但不确定从哪里开始，可以考虑：

- 改进文档：发现任何文档不清晰或有错误，欢迎直接 PR；
- 增加示例：在 `userspace/strategies/` 下增加新的示例策略；
- 完善测试：为核心模块补充单元/集成测试；
- 性能优化：围绕数据加载、数据库访问、多进程/多线程执行提出优化建议或 PR。

非常欢迎你在 issue 区介绍自己的使用场景与需求，这也有助于我们一起打磨框架。感谢你的贡献！

