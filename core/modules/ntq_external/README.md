# NtqExternal（`modules.ntq_external`）

**模块：** `modules.ntq_external` · **版本：** `0.1.0`

NTQ 与官网之间的唯一客户端：对外地址、会员资料与会员 AI 通道、应用内反馈、trace 发送端。

## 适用场景

- 需要官网页面地址：免责声明、许可协议、联系我们、注册、文档
- 读取会员资料：昵称、头像、点数、档位、猫粮余额
- 经官网会员通道调用 AI（模型密钥留在官网，本机只持通用凭证）
- 应用内软反馈：提交评分与文字、控制提示频率
- 向 `infra.trace` 登记官网接收端

## 目录

| 路径 | 说明 |
|------|------|
| `site.py` | 给其他模块的页面地址集合 |
| `conf/` | 对外地址的唯一来源（生产默认值 + 运行时覆盖） |
| `member_profile.py` | 会员资料查询与访客态归一化 |
| `ai/` | 会员 AI 通道：凭证、根地址、额度与流水 |
| `feedback/` | 应用内软反馈门面与本地偏好 |
| `track/` | 向 `infra.trace` 登记官网发送端 |

## 模块依赖

- `infra.membership`
- `infra.project_context`
- `infra.trace`
## 设计初衷

- **地址只认一处。** `conf/site_target.py` 是全部对外 URL 的唯一来源；其他模块经 `site_urls()` 取页面地址，不自己拼字符串。
- **凭证不进响应。** 会员资料只返回业务字段；请求凭证来自 `infra.membership`，响应里不出现。
- **故障与未登录分开。** 资料查询区分 `missing`（无凭证）、`rejected`（官网拒绝）、`unreachable`（网络不可达），避免把断网说成未注册。
- **安装事件不问同意。** trace 发送端在模块导入时登记，安装事件不受使用统计开关影响；其余事件仍由 `infra.trace` 按用户同意处理。
- **明确不做：** 不保存模型密钥、不做登录注册流程（跳转官网）、不做支付与订单。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
