# Membership — 架构

**模块：** `infra.membership` · **版本：** `0.1.0`

## 职责与边界（结论）

官网会员通用凭证的本地存取。**只负责凭证存储与格式校验**，不做在线验证、不回传明文给 HTTP 层。

**职责：**

- 从 `userspace/system/membership/membership_token.txt` 读取凭证
- 写入新凭证（格式校验 + chmod 0600）
- 查询凭证状态（configured / invalid / missing）
- 清除凭证文件

**不做：**

- 在线验证 / 续期（那是 `modules.ntq_external` 走官网的事）
- 回传明文给 HTTP 层
- 会员资料查询（`ntq_external.member_profile` 管）

## 模块结构图

```text
infra/membership/
├── membership.py            # Facade：Membership（5 个静态方法）
├── __init__.py              # 导出 Membership
├── API.md                   # 公开调用面
├── glossary.yaml            # 术语表
└── __test__/                # 含 test_api.py
```

## 架构图

```
Settings 页（CLI / UI）
  → Membership.save(token)     # 格式校验 + 写盘 + chmod
其他模块（ntq_external / Agent）
  → Membership.status()        # 返回 configured / invalid / missing
  → Membership.read()          # 只返回状态，不回传明文
```

## 数据流（若有）

无显著数据流——凭证文件每次按需读写，不做缓存。

## 依赖（结论）

| 依赖 | 用途 |
|------|------|
| `infra.project_context` | 定位凭证文件存储路径 |

## 相关文档

- [用户指南](./USER_GUIDE.md)
- [README.md](../README.md)
- [公开 API](../API.md)
- [术语表](../glossary.yaml)
