# Membership（`infra.membership`）

**模块：** `infra.membership` · **版本：** `0.1.0`

官网会员通用凭证的读写与状态查询：设置页把凭证写入 userspace，后续会员功能只读状态与凭证。对外门面类（Facade）为 `Membership`。

## 适用场景

- 设置页 / CLI 写入、查看或清除官网会员凭证
- 会员功能（如 ntq_external）读取凭证状态，判断会员能力是否可用

## 模块依赖

- `infra.project_context`：定位凭证文件（`userspace/system/membership/membership_token.txt`）

## 设计初衷

- **要解决的问题：** 把凭证存放位置、格式校验（`ntq_` + 48 位十六进制）、权限收紧（0600）收在一个入口，各会员功能不各自读文件。
- **明确不做：** 不回传明文凭证——HTTP / 上层只暴露 `status` / `save` / `clear`；不做在线验证与续期（属 ntq_external）。

## 常见问题

**Q：凭证格式不对怎么办？**
A：`save` 返回错误文案，不写文件；`status` 的 `invalid` 为 `true` 表示文件存在但内容不是有效凭证。

**Q：凭证文件里能写注释吗？**
A：可以。`#` 开头的行与空行会跳过，取第一行有效内容。

**Q：该 import 什么？**
A：`from core.infra.membership import Membership`；包根只导出 `Membership`。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
