# Stocks-Py 文档中心

欢迎来到 Stocks-Py 文档中心！这里汇集了所有项目文档，帮助您快速上手和深入理解系统。

## 📚 文档导航

### 🚀 快速入门

适合新用户和初次使用者：

- [安装指南](getting-started/installation.md) - 环境配置和依赖安装
- [虚拟环境使用](getting-started/venv-usage.md) - Python 虚拟环境管理
- [配置指南](getting-started/configuration.md) - 数据库和系统配置

### 👥 用户指南

适合基于平台进行二次开发的开发者：

- [用户指南首页](../user-guide/README.md) - 用户指南导航
- [策略开发指南](../user-guide/strategy-development.md) - 如何开发自定义策略
- [数据源使用指南](../user-guide/data-source-usage.md) - 数据源 Handler 和 Provider 开发
- [标签系统指南](../user-guide/tag-system.md) - 标签场景开发和使用
- [示例集合](../user-guide/examples.md) - 完整示例代码和教程

### 🏗️ 架构文档

适合深入理解系统设计的开发者：

- [系统架构概览](architecture/overview.md) - 整体架构和设计理念，串联所有模块
- [DataManager 架构](architecture/data_manager_architecture.md) - 数据管理器设计
- [Strategy 框架架构](architecture/strategy_architecture.md) - 策略框架设计
- [DataSource 架构](architecture/data_source_architecture.md) - 数据源系统设计
- [Tag 系统架构](architecture/tag_architecture.md) - 标签系统设计

### 📖 API 参考

适合需要查看具体 API 的开发者：

- [DataManager API](api-reference/data-manager.md) - 数据管理器接口文档
- [Strategy Components API](api-reference/strategy-components.md) - 策略组件接口
- [Infrastructure API](api-reference/infrastructure.md) - 基础设施接口

### 🔧 开发文档

适合项目贡献者和维护者：

- [测试指南](development/testing.md) - 测试框架和覆盖率
- [代码规范](development/code-style.md) - 代码风格和规范
- [贡献指南](development/contributing.md) - 如何参与项目开发
- [覆盖率配置](development/coverage.md) - 测试覆盖率配置
- [路线图](development/road-map.md) - 项目发展规划

## 🎯 按角色查找

### 我是新用户
1. 阅读 [安装指南](getting-started/installation.md)
2. 查看 [配置指南](getting-started/configuration.md)
3. 参考 [示例集合](../user-guide/examples.md)

### 我要开发策略
1. 阅读 [策略开发指南](../user-guide/strategy-development.md)
2. 查看 [Strategy 框架架构](architecture/strategy_architecture.md)
3. 参考示例策略代码

### 我要开发数据源
1. 阅读 [数据源使用指南](../user-guide/data-source-usage.md)
2. 查看 [DataSource 架构](architecture/data_source_architecture.md)
3. 参考现有 Handler 实现

### 我要理解系统架构
1. 阅读 [系统架构概览](architecture/overview.md) - 了解整体架构
2. 深入各模块架构文档：
   - [DataManager 架构](architecture/data_manager_architecture.md)
   - [Strategy 框架架构](architecture/strategy_architecture.md)
   - [DataSource 架构](architecture/data_source_architecture.md)
   - [Tag 系统架构](architecture/tag_architecture.md)
3. 查看 [API 参考](api-reference/)

## 📝 文档维护

- **文档位置**：
  - `docs/` - 项目文档（安装、架构、开发等）
  - `user-guide/` - 用户指南（策略开发、数据源使用等）
- **模块文档**：各模块的 `README.md` 保留为快速使用指南
- **详细文档**：架构和设计文档统一在 `docs/architecture/`
- **更新原则**：只保留当前版本文档，历史文档已归档或删除

## 🔗 相关链接

- [项目主页](../README.md) - 返回项目主 README
- [GitHub/Gitee 仓库](https://gitee.com/your-repo) - 源代码仓库
- [问题反馈](https://gitee.com/your-repo/issues) - 提交 Issue

---

**最后更新**：2026-01-17
