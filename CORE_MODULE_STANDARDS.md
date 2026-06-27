# NTQ Core Module Standards - 核心模块创建与维护准则

**版本：** 1.0.0
**最后更新：** 2026-06-26
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
- 合理使用缓存（如PathManager的userspace缓存）
- 性能测试（关键API应该有性能测试）

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
| `__test__/test_*.py` | Python文件 | 单元测试 | 文件存在 |

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
| `每个API的example字段` | string | 使用示例 | 属性存在 |

---

### **指标6：api.py内容要求**

> api.py必须定义抽象接口

**必需内容：**

| 内容 | 类型 | 说明 | 检查方式 |
|------|------|------|---------|
| `ABC类` | class | 抽象接口类 | 文件包含ABC类 |
| `@classmethod + @abstractmethod` | decorator | 类方法抽象 | 方法使用正确的decorator |
| `所有对外API` | method | 所有核心API | api.py和api.yaml的API数量一致 |

---

### **指标7：__init__.py导出要求**

> __init__.py必须正确导出Facade类

**必需导出：**

| 导出项 | 类型 | 说明 | 检查方式 |
|--------|------|------|---------|
| `Facade类` | class | 对外唯一入口 | __init__.py导出Facade类 |
| `ABC类` | class | 抽象接口 | __init__.py导出ABC类 |
| `__all__` | list | 导出列表 | __all__包含Facade类和ABC类 |

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
| ✅ 删除冗余代码 | 理念 | 删除不再使用的代码 |
| ✅ 收紧核心模块 | 理念 | Facade模式，单一入口点 |
| ✅ 文件结构完整 | 硬性指标 | 所有必需文件存在 |
| ✅ 文档更新 | 硬性指标 | 文档反映最新状态 |

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

**最后更新：** 2026-06-26
**维护者：** NTQ Team