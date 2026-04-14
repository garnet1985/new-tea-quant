# 用户指南

欢迎来到 New Tea Quant 用户指南！本指南面向基于平台进行二次开发的开发者，帮助您快速上手和深入使用框架。

## 📚 指南导航

### 🎯 策略开发

- [策略开发指南](strategy-development.md) - 如何开发自定义策略
  - 创建策略目录和文件
  - 实现策略逻辑
  - 配置策略参数
  - 运行和测试策略

### 📊 数据源开发

- [数据源使用指南](data-source-usage.md) - 数据源 Handler 和 Provider 开发
  - 创建自定义 Handler
  - 使用现有 Provider
  - 配置数据源映射
  - 数据标准化

### 🏷️ 标签系统

- [标签系统指南](tag-system.md) - 标签场景开发和使用
  - 创建标签场景
  - 实现标签计算逻辑
  - 在策略中使用标签
  - 标签数据查询

### 📖 示例集合

- [示例集合](examples.md) - 完整示例代码和教程
  - 策略示例
  - 数据源示例
  - 标签示例
  - 适配器示例

## 🚀 快速开始

### 1. 开发第一个策略

1. 阅读 [策略开发指南](strategy-development.md)
2. 参考 [示例策略](../../userspace/strategies/example/)
3. 运行策略测试

### 2. 开发数据源 Handler

1. 阅读 [数据源使用指南](data-source-usage.md)
2. 参考 [数据源用户指南](../../userspace/data_source/USER_GUIDE.md)
3. 查看现有 Handler 实现

### 3. 使用标签系统

1. 阅读 [标签系统指南](tag-system.md)
2. 参考 [示例标签场景](../../userspace/tags/momentum/)
3. 在策略中集成标签

## 📖 相关文档

### 项目文档

- [文档中心](../docs/README.md) - 项目文档导航
- [安装指南](../docs/getting-started/installation.md) - 环境配置
- [配置指南](../docs/getting-started/configuration.md) - 系统配置

### 架构文档

- [系统架构概览](../docs/architecture/overview.md) - 整体架构
- [Strategy 框架架构](../docs/architecture/strategy_architecture.md)
- [DataSource 架构](../docs/architecture/data_source_architecture.md)
- [Tag 系统架构](../docs/architecture/tag_architecture.md)

### 模块文档

- [Strategy README](../core/modules/strategy/README.md)
- [DataSource README](../core/modules/data_source/README.md)
- [Tag README](../core/modules/tag/README.md)

## 🎯 按需求查找

### 我要开发策略
→ [策略开发指南](strategy-development.md) → [示例策略](../../userspace/strategies/example/)

### 我要开发数据源
→ [数据源使用指南](data-source-usage.md) → [数据源用户指南](../../userspace/data_source/USER_GUIDE.md)

### 我要使用标签
→ [标签系统指南](tag-system.md) → [示例标签场景](../../userspace/tags/momentum/)

### 我要看示例代码
→ [示例集合](examples.md)

## 💡 提示

- **从示例开始**：建议先查看示例代码，理解基本用法
- **参考架构文档**：深入理解系统设计，更好地使用框架
- **查看模块文档**：各模块的 README 包含详细的使用说明
- **提问反馈**：遇到问题可以在 Gitee Issues 中提问

---

**最后更新**：2026-01-20
