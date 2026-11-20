# NtqExternal API 文档

**模块：** `modules.ntq_external` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.6.0`

> 须与 `module_info.yaml` 一致。core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `register_trace_endpoint` 与 `site_urls`。会员资料、反馈为**模块间入口**，由 `data_source`、UI/BFF 直接使用子包；普通调用方不需要感知。

---

## site_urls

`site_urls() -> dict`

- **类型：** 模块级函数
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 返回官网页面地址。调用方拿不到本模块时，应视为没有官网入口
- **参数：** 无
- **返回值：** `dict`，固定键：

| 键 | 类型 | 说明 |
|----|------|------|
| `disclaimer_url` | `str` | 免责声明 |
| `license_url` | `str` | 许可协议 |
| `contact_url` | `str` | 联系我们 |
| `register_url` | `str` | 注册 / 登录 |
| `docs` | `dict` | 文档页：`strategy` / `opportunities` / `tag` / `datasource` / `contract` |

- **举例：**

```python
from core.modules.ntq_external import site_urls

urls = site_urls()
print(urls["register_url"])
```

## register_trace_endpoint

`register_trace_endpoint() -> None`

- **类型：** 模块级函数
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 把官网 trace 地址登记到 `infra.trace`。**模块导入时已自动调用一次**；安装事件不受使用统计开关约束
- **参数：** 无
- **返回值：** `None`
- **错误与异常：** 不抛业务异常；登记失败由 `infra.trace` 自行处理

---

## 模块间入口

以下入口不经包根导出，供已有调用方使用。字段变更须同步本表与 `__test__/TEST_CASES.md`。

### Feedback

`from core.modules.ntq_external.feedback import Feedback`

静态门面，所有方法不抛异常、失败不影响调用方。

| 方法 | 签名 | 说明 |
|------|------|------|
| `submit` | `(*, rating, text="", source="popup", meta=None) -> bool` | 提交一条反馈；返回 HTTP 是否受理 |
| `note_task_success` | `(*, source="") -> dict` | 记录一次任务成功，可能返回 `should_prompt=True` |
| `snooze_prompt` | `() -> bool` | 本次稍后再提示 |
| `disable_prompts` | `(*, source="popup") -> bool` | 不再提示（可在设置中重新开启） |
| `get_prefs` | `() -> dict` | 读取本地提示偏好 |
| `set_prompts_disabled` | `(disabled, *, source="settings_ui") -> bool` | 设置是否禁用提示 |
| `contact_url` | `() -> str` | 联系我们页面地址 |

### install_demo

`from core.modules.ntq_external.install_demo import download_install_demo, resolve_install_demo_url`

公开演示安装包（无需会员凭证）。供 `infra.setup` 在本地无 zip 时拉取。

| 符号 | 签名 | 说明 |
|------|------|------|
| `resolve_install_demo_url` | `() -> str` | 下载 URL；可用 `NTQ_INSTALL_DEMO_URL` 覆盖 |
| `resolve_install_demo_meta_url` | `() -> str` | meta URL；可用 `NTQ_INSTALL_DEMO_META_URL` 覆盖 |
| `fetch_install_demo_meta` | `(*, timeout_sec=30.0) -> dict` | 拉取 meta JSON |
| `download_install_demo` | `(dest_dir, *, force=False, timeout_sec=120.0) -> Path` | 写入 `dest_dir/data_demo.zip`；已存在且非 force 则跳过；有 meta 时校验 sha256 |

失败抛 `InstallDemoError`。

### member_profile

`from core.modules.ntq_external.member_profile import member_profile`

`member_profile() -> dict`

已登录时返回会员资料；否则返回访客态。**响应中不含凭证。**

| 字段 | 类型 | 说明 |
|------|------|------|
| `signed_in` | `bool` | 是否已登录 |
| `reason` | `str \| None` | 访客原因：`missing` / `rejected` / `unreachable`；已登录时为 `None` |
| `name` / `avatar` | `str \| None` | 昵称、头像 URL |
| `points` | `int \| None` | 点数；访客为 `None` |
| `tier` | `str \| None` | `standard` / `pro`；访客为 `None` |
| `is_pro` | `bool` | 是否 Pro |
| `catfood` | `float \| None` | 猫粮余额 |
| `token_balance` | `int \| None` | token 余额 |
| `currency` | `str \| None` | 币种 |
| `sync_access` | `str \| None` | 数据同步范围：`demo` / `all`；访客为 `None` |
| `register_url` | `str` | 注册地址 |

- **举例：**

```python
from core.modules.ntq_external.member_profile import member_profile

profile = member_profile()
if profile["signed_in"]:
    print(profile["name"], profile["tier"])
```

---

## contracts

本模块无独立契约文件；`Feedback` 与 `member_profile` 的返回结构即上表。
