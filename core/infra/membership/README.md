# Membership（`infra.membership`）

**模块：** `infra.membership` · **版本：** `0.1.0`

**最低支持核心版本：** `>=0.5.3`

## 简介

官网会员凭证的本地存取。设置页把凭证写进 userspace，其他模块（ntq_external）只来这里读状态和凭证内容。格式校验、文件权限收紧、注释行跳过这些细节都在这里。**不**回传明文给 HTTP 层。

## 适用场景

- 设置页里让用户粘贴官网会员中心显示的通用凭证
- Agent 或 ntq_external 想知道用户是不是会员、凭证有效不

## 模块依赖

- `infra.project_context`：定位凭证文件存储路径

## 设计初衷

- **要解决的问题：** 凭证存放位置、格式校验、权限不能让每个会员功能自己处理一遍。
- **明确不做：** 不做在线验证、不续期（那是 ntq_external 走官网的事）；不回传明文给 HTTP 层。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
