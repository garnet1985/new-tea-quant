# NTQ Core Module Standards - 核心模块创建与维护准则

**版本：** 1.1.0
**最后更新：** 2026-06-30
**适用范围：** 所有 core 目录下的模块

---

## 📋 目的

本文档定义了 NTQ 项目核心模块的创建、维护和清理准则，确保：
- **一致性**：所有核心模块遵循相同的规范
- **可维护性**：强规则优于灵活性，便于长期维护
- **稳定性**：API契约明确，避免破坏性变更

---

## 🎯 设计理念（抽象原则）

> 理念是指导原则，不可自动化检查，需要人工判断和决策

### **理念1：收紧核心模块**

> 核心模块需要收紧，不要多个文件提供相同功能的API

**原因：**
- 避免用户混淆，不知道该调用哪个API
- 减少维护成本，不需要同时维护多个入口点
- 确保API契约稳定，不会因为多个入口点导致不一致

**实践：**
- 每个核心模块应该有一个Facade类（对外唯一入口）
- 内部实现私有化（内部Manager不对外暴露）
- 抽象接口明确（所有对外API在抽象类中定义）

---

### **理念2：强规则优于灵活性**

> 核心模块不需要灵活，而是强规则，这样才好维护

**原因：**
- 灵活性导致维护成本增加
- 强规则确保一致性，减少错误
- 用户不需要学习多种方式，简单清晰

**实践：**
- 单一调用方式（所有API使用类方法）
- 统一命名规范（遵循CODE_STYLE.md）
- 统一错误处理（所有API使用相同的错误处理策略）

---

### **理念3：术语统一**

> 核心模块需要有术语表，术语需要统一，不要出现多个术语描述同一个事物

**原因：**
- 避免混淆，不同模块使用相同的术语
- 减少沟通成本，术语一致便于理解

**实践：**
- 定义术语表（glossary.yaml）
- 遵循术语表（所有代码、文档、注释遵循术语表）
- 及时更新（发现新的术语冲突，及时更新术语表）

---

### **理念4：版本管理**

> 核心模块需要有版本号，遵循语义化版本规范

**原因：**
- 明确模块版本，便于管理依赖
- 记录变更历史，便于追溯

**实践：**
- 语义化版本（MAJOR.MINOR.PATCH）
- 版本一致性（所有文档使用相同的版本号）
- 变更记录（每次改动都记录在changelog）

---

### **理念5：依赖管理**

> 核心模块需要明确依赖关系，避免循环依赖

**原因：**
- 依赖关系清晰，便于理解模块关系
- 避免循环依赖，确保模块独立性

**实践：**
- 依赖列表明确（module_info.yaml中明确依赖）
- 避免循环依赖（依赖关系应该是单向的）
- 最小依赖原则（尽量减少依赖数量）

---

### **理念6：性能考虑**

> 核心模块需要考虑性能，避免过度抽象

**原因：**
- 核心模块使用频率高，性能影响大
- 过度抽象导致性能下降

**实践：**
- 避免过度抽象（不要为了"灵活性"过度设计）
- 合理使用缓存（如 PathManager 的 userspace 缓存）
- 调度参数用 dataclass 在入口一次 `validate()` / `resolve()`，避免 dict 在内部重复校验

---

### **理念7：配置边界清晰**

> 核心模块只定义 base defaults + validate/resolve；业务调优配置归属应用层，用户 settings 不可覆盖运行参数

**原因：**
- 避免 global worker.json 与模块 settings 多层 merge 导致行为不可预期
- 性能调优由基准测试得出，不应暴露给用户随意改动
- engine 入口一次 validate，内部不再散落 `"auto"` 判断

**实践（以 backtest_engine 为参考）：**
- engine：`EntityBasedPerformance.base()` + 应用方 override → `validate()` → `resolve_for_planning()`
- 应用层：模块内 `settings/dispatch.yaml`（或等价常量），run 前 load 并传入 `BacktestEngine.run(performance=...)`
- 用户 settings：只含业务字段（如 `update_mode`、`run_options.dry_run`），**禁止** `settings["performance"]`
- engine **不**读取 `core/default_config/worker.json` 的 dispatch 段
- infra 能力（如 `MachineInfo`）直接从 `core.infra.*` 导入，**禁止**在模块内建 re-export 空壳文件

---

### **理念8：进度与可观测性内聚**

> 调度类核心模块在 engine 层统一计算进度；显示开关与计算逻辑分离

**实践：**
- 进度始终计算（分阶段权重 + execute 单元计数）
- API 参数如 `enable_progress_display` 仅控制 CMD/日志输出，不影响内部计数
- slice 等细粒度进度通过 engine 注入的 hook（如 `_engine_on_execute_unit_done`）由 orchestrator 回调，不重复在业务层拼 percent

---

## ✅ 硬性指标（可自动化检查）

> 硬性指标是具体要求，可以自动化检查，确保模块符合规范

### **指标1：文件结构要求**

> 核心模块必须有完整的文件结构

**必需文件：**

| 文件路径 | 文件类型 | 说明 | 检查方式 |
|---------|---------|------|---------|
| `api.yaml` | YAML文件 | API契约文档 | 文件存在 |
| `api.py` | Python文件 | 抽象接口定义 | 文件存在，包含ABC类 |
| `__init__.py` | Python文件 | 导出Facade类 | 文件存在，包含Facade类导出 |
| `module_info.yaml` | YAML文件 | 模块元数据 | 文件存在 |
| `glossary.yaml` | YAML文件 | 统一术语表 | 文件存在 |

---

### **指标2：测试文件要求**

> 核心模块必须有测试覆盖

**必需测试文件：**

| 文件路径 | 文件类型 | 说明 | 检查方式 |
|---------|---------|------|---------|
| `__test__/test_api.py` | Python文件 | API契约测试 | 文件存在，包含API测试 |
| `__test__/test_cases.yaml` | YAML文件 | 测试用例注册表（推荐） | case id + scenarios + 对应 test 文件 |
| `__test__/test_*.py` | Python文件 | 单元测试 | 文件存在，与 test_cases.yaml 对齐 |

---

### **指标3：文档文件要求**

> 核心模块必须有文档

**必需文档文件：**

| 文件路径 | 文件类型 | 说明 | 检查方式 |
|---------|---------|------|---------|
| `docs/ARCHITECTURE.md` | Markdown文件 | 架构设计 | 文件存在 |
| `docs/DESIGN.md` | Markdown文件 | 详细设计 | 文件存在 |
| `docs/DECISIONS.md` | Markdown文件 | 设计决策 | 文件存在 |

---

### **指标4：module_info.yaml内容要求**

> module_info.yaml必须有必需属性

**必需属性：**

| 属性名 | 类型 | 说明 | 检查方式 |
|--------|------|------|---------|
| `name` | string | 模块名称 | 属性存在 |
| `version` | string | 版本号 | 属性存在，格式正确 |
| `compatible_core_versions` | string | 兼容版本 | 属性存在 |
| `description` | string | 模块描述 | 属性存在 |
| `dependencies` | list | 依赖列表 | 属性存在 |
| `changelog` | list | 变更历史 | 属性存在，有至少一条记录 |

---

### **指标5：api.yaml内容要求**

> api.yaml必须有必需属性

**必需属性：**

| 属性名 | 类型 | 说明 | 检查方式 |
|--------|------|------|---------|
| `Version` | string | 版本号 | 属性存在，格式正确 |
| `apis` | dict | API列表 | 属性存在，有至少一个API |
| `Requires` | string | 最小兼容版本 | 属性存在，如 `core>=0.3.0` |

**禁止项：**
- ❌ 删除冗余Examples字段（示例已在API定义中提供）
- ❌ 不要重复描述参数和返回值（已在API定义中说明）

---

### **指标6：api.py内容要求**

> api.py必须定义Facade类和namespace API

**必需内容：**

| 内容 | 类型 | 说明 | 检查方式 |
|------|------|------|---------|
| `模块名.py` | file | 模块主文件 | 文件名与模块名一致（如 discovery.py） |
| `Facade类` | class | 对外唯一入口 | 类名简洁（如 Discovery, ProjectContext） |
| `namespace API` | method | 嵌套结构API | API使用命名空间（如 Discovery.file.xxx） |

**禁止项：**
- ❌ 不使用 api.py 命名（使用模块名.py）
- ❌ 不定义ABC类（使用Facade类）
- ❌ 不使用抽象方法（使用具体实现）
- ❌ 不暴露class和便捷函数

---

### **指标7：__init__.py导出要求**

> __init__.py 仅导出 Facade；对外契约放在根目录独立模块（如 `contracts.py`）

**必需导出：**

| 导出项 | 类型 | 说明 | 检查方式 |
|--------|------|------|---------|
| `Facade类` | class | 对外主入口 | __init__.py 导出 Facade 类 |

**契约模块（根目录，跨模块 import 入口）：**

| 文件 | 导出项 | 说明 |
|------|--------|------|
| `contracts.py` | dataclass / enum | 如 `JobContext`、`JobReport`、`RunProgress` |
| `jobs.py` | helper class | 如 `BacktestJob.from_dict` |

**禁止项：**
- ❌ 不在 __init__.py 堆叠契约 re-export（难以发现、IDE 跳转差）
- ❌ 不导出内部实现类（如 `TimelineExecutor`、`SlicePlanner`）
- ❌ 不导出便捷函数（除非文档明确列为 public API）
- ❌ 不保留向后兼容 proxy 函数
- ❌ 不为 infra 类型建 re-export 空壳（如 `machine_info.py` 仅 `from core.infra import X`）— 调用方直接 import infra

---

### **指标8：文档内容要求**

> 文档必须有必需内容

**必需内容：**

| 文档 | 必需内容 | 检查方式 |
|------|---------|---------|
| `docs/ARCHITECTURE.md` | 版本号、架构设计、API分组 | 文件包含必需内容 |
| `docs/DESIGN.md` | 版本号、详细设计、设计原则 | 文件包含必需内容 |
| `docs/DECISIONS.md` | 版本号、设计决策、决策列表 | 文件包含必需内容 |

---

### **指标9：文件命名规范**

> 核心模块文件命名必须遵循统一规范

**命名规则：**

| 文件类型 | 命名规范 | 示例 | 检查方式 |
|---------|---------|------|---------|
| 模块名.py | 对外暴露API | `discovery.py`, `project_context.py` | 文件存在，文件名与模块名一致 |
| 内部实现文件夹 | 使用 `core/` | `core/` 子目录存在 | 不使用 `_impl/`, `modules/` 等命名 |
| 根目录文件 | 只保留必需文件 | 模块名.py、api.yaml、module_info.yaml、glossary.yaml、__init__.py、contracts.py 等契约入口 | 根目录文件数量符合要求 |

**禁止项：**
- ❌ 不使用 `_impl/` 命名内部实现目录
- ❌ 不使用 `modules/` 命名内部实现目录
- ❌ 根目录不保留冗余文件

---

### **指标10：API暴露方式**

> 核心模块 API 暴露遵循 Facade 模式；契约类型从根目录独立模块导入

**暴露规则：**

| 要求 | 规范 | 检查方式 |
|------|------|---------|
| 主入口为 Facade 类 | 如 `Discovery`, `BacktestEngine` | __init__.py 导出 Facade |
| 契约 types 独立模块 | dataclass / enum / wire helper | 根目录 `contracts.py` 等 |
| 使用 namespace API（可选） | 如 `Discovery.file.xxx` | 嵌套结构 |
| 不暴露内部 executor/planner | 实现细节留在 `core/` | 跨模块不 import `core/` |
| 不保留向后兼容 proxy | 不提供旧 API 代理函数 | 代码中无兼容 proxy |

**示例：**
```python
# ✅ 推荐：Facade + 根目录契约模块
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks
from core.modules.backtest_engine.core.performance.worker_profile import (
    WorkerProfiles,
    resolve_entity_based_performance_for_profile,
)

result = BacktestEngine.entity_based.run(
    jobs,
    execute_fn,
    performance=resolve_entity_based_performance_for_profile(WorkerProfiles.TAG),
    task_name="tag:demo",
    callbacks=RunCallbacks(on_result=handle_result),
    enable_progress_display=True,
)

# ❌ 禁止：跨模块 import 内部路径
from core.modules.backtest_engine.core.timeline_based.planner import TimelinePlanner

# ❌ 禁止：用户 settings 传入 performance
settings["performance"] = {"max_workers": 8}
```

---

### **指标14：test_cases.yaml 测试注册表（推荐）**

> 核心模块在 `__test__/test_cases.yaml` 维护测试索引；测试脚本与 case 对齐

**结构：**

```yaml
cases:
  - id: 1
    case: api                    # 大类名
    description: "公开 API 与 Mode 枚举"
    file: test_api.py            # 一个 case 对应一个 test 文件（无 file 则仅文档/手工）
    scenarios:
      - id: 1
        name: test_facade_export # 与 pytest 函数名一致
        description: "..."
```

**规则：**
- `id` 为整数，case 内 scenario `id` 从 1 递增
- 每个 `file` 只出现一次；scenario 在文件内用函数名区分
- 不测试 infra 职责的模块应删除对应 case（如 MachineInfo 测在 `core/infra`）
- 集成测试留在业务模块 `__test__`，engine 层保持纯单元测试

**参考：** `core/modules/backtest_engine/__test__/test_cases.yaml`

---


> 核心模块版本号更新必须遵循规范

**版本更新规则：**

| 变更类型 | 是否更新版本号 | 示例 |
|---------|---------------|------|
| 小改动（修复bug、优化代码） | ❌ 不更新 | 修复文档错误、优化性能 |
| 分支没变（同一开发分支） | ❌ 不更新 | 同一分支上的多次提交 |
| 中版本变化（新增功能、重构API） | ✅ 更新 | 0.3.0 → 0.4.0 |
| 大版本变化（架构变更） | ✅ 更新 | 0.4.0 → 1.0.0 |

**版本号格式：**
- 遵循语义化版本规范：`MAJOR.MINOR.PATCH`
- 0.x 版本表示开发阶段，可以颠覆性改动

---

### **指标12：代码注释规范**

> docstring 一句话说明「做什么」；签名/类型已表达的信息不重复；对外契约在 `api.yaml` / `OVERVIEW.md`

**注释规则：**

| 注释类型 | 是否保留 | 说明 |
|---------|---------|------|
| 一行 docstring（做什么） | ✅ 保留 | 公开/内部函数均可 |
| 复杂逻辑行内注释 | ✅ 保留 | 解释非显而易见的算法或分支 |
| 冗余 docstring（Args/Returns/Examples） | ❌ 不写 | 类型注解 + `api.yaml` 已覆盖 |
| 冗余 docstring（Note/使用方式） | ❌ 不写 | 见 `OVERVIEW.md` / 架构文档 |

**示例：**
```python
# ✅ 推荐：只保留必要注释
def calculate_weighted_average(prices: List[float], weights: List[float]) -> float:
    """
    计算加权平均值
    """
    # 使用对数加权避免数值溢出（复杂逻辑需要注释）
    log_weights = np.log(weights + 1e-10)
    return np.sum(prices * np.exp(log_weights)) / np.sum(np.exp(log_weights))

# ❌ 禁止：冗余注释
def find_file(filename: str) -> Path:
    """
    查找文件

    Args:
        filename: 文件名  # ❌ 冗余，已在 api.yaml 中说明

    Returns:
        文件路径  # ❌ 冗余，已在 api.yaml 中说明

    Examples:  # ❌ 冗余，已在 api.yaml 中提供
        >>> find_file("config.yaml")
        /path/to/config.yaml

    Note:  # ❌ 冗余，应在文档中说明
        该函数会递归搜索
    """
    pass
```

---

### **指标13：不保留兼容性**

> 核心模块在0.x版本可以颠覆性改动

**兼容性规则：**

| 版本范围 | 允许的改动 | 要求 |
|---------|-----------|------|
| 0.x 版本 | ✅ 颠覆性改动 | 直接改动，不保留旧API |
| 1.x 版本 | ⚠️ 向后兼容 | 保留旧API，添加废弃警告 |
| 2.x+ 版本 | ⚠️ 向后兼容 | 遵循语义化版本规范 |

**实践：**
- ✅ 直接改动，不保留旧API
- ❌ 不保留平铺API作为proxy
- ❌ 不保留旧类名作为alias

**示例：**
```python
# ✅ 推荐：0.x版本直接改动
# 旧版本 0.3.0
# find_file("config.yaml")

# 新版本 0.4.0
# Discovery.file.find_file("config.yaml")

# ❌ 禁止：保留向后兼容proxy
def find_file(*args, **kwargs):
    """已废弃，请使用 Discovery.file.find_file"""
    warnings.warn("find_file is deprecated, use Discovery.file.find_file")
    return Discovery.file.find_file(*args, **kwargs)

# ❌ 禁止：保留旧类名
FileUtils = Discovery  # 不允许alias
```

---

## 📊 自动化检查脚本

### **检查脚本示例**

```python
#!/usr/bin/env python3
"""
核心模块标准检查脚本
"""

import os
import yaml
from pathlib import Path
from typing import List

def check_core_module(module_path: Path) -> List[str]:
    """检查核心模块是否符合标准"""
    errors = []
    
    # 检查必需文件
    required_files = [
        "api.yaml",
        "api.py",
        "__init__.py",
        "module_info.yaml",
        "glossary.yaml",
        "docs/ARCHITECTURE.md",
        "docs/DESIGN.md",
        "docs/DECISIONS.md",
    ]
    
    for file in required_files:
        if not (module_path / file).exists():
            errors.append(f"缺少必需文件：{file}")
    
    # 检查module_info.yaml内容
    module_info_path = module_path / "module_info.yaml"
    if module_info_path.exists():
        module_info = yaml.safe_load(module_info_path.read_text())
        required_attrs = ["name", "version", "description", "dependencies", "changelog"]
        for attr in required_attrs:
            if attr not in module_info:
                errors.append(f"module_info.yaml缺少必需属性：{attr}")
    
    # 检查api.yaml内容
    api_yaml_path = module_path / "api.yaml"
    if api_yaml_path.exists():
        api_yaml = yaml.safe_load(api_yaml_path.read_text())
        if "apis" not in api_yaml:
            errors.append("api.yaml缺少必需属性：apis")
    
    # 检查测试文件
    test_api_path = module_path / "__test__/test_api.py"
    if not test_api_path.exists():
        errors.append("缺少必需测试文件：__test__/test_api.py")
    
    return errors

# 使用示例
module_path = Path("/path/to/core/module")
errors = check_core_module(module_path)
if errors:
    print("❌ 模块不符合标准：")
    for error in errors:
        print(f"  {error}")
else:
    print("✅ 模块符合标准")
```

---

## 🎯 检查清单

### **创建新模块检查清单**

| 检查项 | 类型 | 说明 |
|--------|------|------|
| ✅ 文件结构完整 | 硬性指标 | 所有必需文件存在 |
| ✅ 测试覆盖完整 | 硬性指标 | API测试和UT测试存在 |
| ✅ 文档齐全 | 硬性指标 | 架构、设计、决策文档存在 |
| ✅ module_info.yaml属性完整 | 硬性指标 | 所有必需属性存在 |
| ✅ api.yaml属性完整 | 硬性指标 | 所有必需属性存在 |
| ✅ api.py包含ABC类 | 硬性指标 | 抽象接口定义存在 |
| ✅ __init__.py正确导出 | 硬性指标 | Facade类正确导出 |
| ✅ 收紧核心模块 | 理念 | Facade模式，单一入口点 |
| ✅ 术语统一 | 理念 | 遵循glossary.yaml |
| ✅ 版本管理 | 理念 | 语义化版本，changelog记录 |
| ✅ 依赖管理 | 理念 | 明确依赖关系 |

---

### **维护模块检查清单**

| 检查项 | 类型 | 说明 |
|--------|------|------|
| ✅ 版本号一致 | 硬性指标 | 所有文档使用相同的版本号 |
| ✅ changelog更新 | 硬性指标 | 记录所有改动 |
| ✅ 文档同步更新 | 硬性指标 | 文档与代码一致 |
| ✅ 测试通过 | 硬性指标 | 所有测试通过 |
| ✅ api.yaml和api.py一致 | 硬性指标 | API数量一致 |
| ✅ 性能考虑 | 理念 | 避免过度抽象 |
| ✅ 强规则优于灵活性 | 理念 | 单一调用方式 |

---

### **清理模块检查清单**

| 检查项 | 类型 | 说明 |
|--------|------|------|
| ✅ 删除冗余API | 理念 | 不要多个文件提供相同功能的API |
| ✅ test_cases.yaml 对齐（推荐） | 硬性指标 | case/scenario 与 test 函数一致 |
| ✅ 删除冗余代码 | 理念 | 无 re-export 空壳、无未使用 default/merge 层 |
| ✅ 文档与代码一致 | 硬性指标 | 不用 backtest_scheduler 等旧模块名 |

---

## 📝 总结

**核心模块的标准分为两部分：**

1. **设计理念（抽象原则）**：指导原则，需要人工判断
   - 收紧核心模块
   - 强规则优于灵活性
   - 术语统一
   - 版本管理
   - 依赖管理
   - 性能考虑
   - 配置边界清晰
   - 进度与可观测性内聚

2. **硬性指标（可自动化检查）**：具体要求，可以自动化检查
   - 文件结构要求
   - 测试文件要求
   - 文档文件要求
   - module_info.yaml内容要求
   - api.yaml内容要求
   - api.py内容要求
   - __init__.py导出要求
   - 文档内容要求

---

**参考文档：**
- [CODE_STYLE.md](file:///Users/garnet/Desktop/new-tea-quant/CODE_STYLE.md) - 代码风格规范（命名规范、编排层+实施层等）
- [glossary.yaml](file:///Users/garnet/Desktop/new-tea-quant/core/infra/project_context/glossary.yaml) - 统一术语表

---

**最后更新：** 2026-06-30
**维护者：** NTQ Team

**模块参考实现：** `core/modules/backtest_engine`（`OVERVIEW.md` + Facade + contracts + `docs/ARCHITECTURE.md` / `docs/DECISIONS.md`）