# 文档结构说明

## 📁 文档组织

项目文档采用**双层结构**，清晰区分项目文档和用户指南：

```
项目根目录/
├── docs/                    # 项目文档（安装、架构、开发等）
│   ├── README.md           # 文档导航首页
│   ├── getting-started/    # 快速入门
│   ├── architecture/       # 架构文档
│   ├── development/        # 开发文档
│   └── api-reference/      # API 参考（待补充）
│
└── user-guide/             # 用户指南（策略开发、数据源使用等）
    ├── README.md           # 用户指南导航
    ├── strategy-development.md
    ├── data-source-usage.md
    ├── tag-system.md
    └── examples.md
```

## 🎯 文档分类

### docs/ - 项目文档

面向所有用户，包含：

- **快速入门** (`getting-started/`)：安装、配置、环境设置
- **架构文档** (`architecture/`)：系统设计、架构概览
- **开发文档** (`development/`)：测试、代码规范、贡献指南
- **API 参考** (`api-reference/`)：API 接口文档

### user-guide/ - 用户指南

面向二次开发者，包含：

- **策略开发指南**：如何开发自定义策略
- **数据源使用指南**：如何开发数据源 Handler 和 Provider
- **标签系统指南**：如何开发和使用标签场景
- **示例集合**：完整的示例代码和教程

## 📝 文档维护原则

1. **集中维护**：
   - `docs/` 目录：项目文档集中管理
   - `user-guide/` 目录：用户指南独立管理

2. **模块文档保留**：
   - 各模块的 `README.md` 保留为快速使用指南
   - 详细架构文档链接到 `docs/architecture/`

3. **只保留当前版本**：
   - 历史文档已归档或删除
   - 避免文档冗余

4. **链接一致性**：
   - 所有文档链接使用相对路径
   - 确保文档间跳转正确

## 🔗 文档链接规则

### 从 docs/ 链接到 user-guide/

```markdown
[用户指南](../user-guide/README.md)
[策略开发指南](../user-guide/strategy-development.md)
```

### 从 user-guide/ 链接到 docs/

```markdown
[文档中心](../docs/README.md)
[安装指南](../docs/getting-started/installation.md)
[架构文档](../docs/architecture/)
```

### 从根目录 README.md 链接

```markdown
[用户指南首页](user-guide/README.md)
[文档中心](docs/README.md)
```

## 📚 文档入口

### 主要入口

1. **项目主 README** (`README.md`)：项目概览和快速链接
2. **文档中心** (`docs/README.md`)：项目文档导航
3. **用户指南** (`user-guide/README.md`)：用户指南导航

### 按角色导航

- **新用户**：`README.md` → `docs/getting-started/`
- **二次开发者**：`README.md` → `user-guide/`
- **架构理解**：`docs/README.md` → `docs/architecture/`
- **项目贡献者**：`docs/README.md` → `docs/development/`

## ✅ 文档完整性检查清单

- [x] 文档目录结构清晰
- [x] 所有文档链接正确
- [x] 文档导航完整
- [x] 示例代码可访问
- [x] 架构文档链接正确
- [x] 用户指南独立管理
- [x] 主 README 更新

---

**最后更新**：2026-01-20
