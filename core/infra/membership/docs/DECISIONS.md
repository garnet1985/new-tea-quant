# Membership — 设计与决策

**模块：** `infra.membership` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.5.3`

本文记录本模块的设计目标、方案思路与拍板决策。  
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

- 官网通用凭证只落在本机 userspace，设置页写入，其它会员能力只读。
- HTTP / UI 只拿 `status`（configured / invalid / path），**绝不回传明文**。
- 格式校验本地完成；在线验真、配额、资料属于 `ntq_external`。

---

## DEC-01：明文不出 HTTP

**是什么：** 公开门面虽有 `read()`，约定仅本机内部（ntq_external / agent / CLI 内部）使用；BFF 设置页只调 `status` / `save` / `clear`。

**为什么：** 凭证等同登录密钥；日志与 API 响应不得带 token。

---

## DEC-02：无 contracts / 无在线逻辑

**是什么：** 模块极薄，无跨模块类型契约文件；不做续期、资料、HTTP。

**为什么：** 状态 dict 与 `Optional[str]` 已够用；业务在 `ntq_external`。

---

## DEC-03：文件名双处声明

**是什么：** 文件名真源在 `project_context.contracts.MEMBERSHIP_TOKEN_FILE_NAME`；`membership_constants.TOKEN_FILE_NAME` 再导出给本模块展示相对路径；绝对路径由 `ProjectContext.path.get_membership_token_file` 给出。

**为什么：** `project_context` 不能依赖 `membership`；两处字面量需人工保持一致。若漂移，优先改 PathManager 与 constants 同名。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
