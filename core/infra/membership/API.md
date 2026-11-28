# Membership API 文档

**模块：** `infra.membership` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.5.3`

> 须与 `module_info.yaml` 一致。
> 本文档是本模块公开调用面的**唯一人读 API 文档**。
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。
> 所列门面入口须有 `__test__/` 覆盖。

术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `Membership`（`from core.infra.membership import Membership`）。本模块无 `contracts.py`。

---

## Membership

**描述：** 官网会员通用凭证门面——读写与状态查询（静态 API，勿实例化）

#### token_file

`Membership.token_file() -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 返回凭证文件路径（`userspace/system/membership/membership_token.txt`）；不保证文件存在
- **参数：** 无
- **返回值：** `Path` — 凭证文件绝对路径
- **举例：**

```python
path = Membership.token_file()
```

#### read

`Membership.read() -> Optional[str]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 读取有效凭证明文；文件不存在、读失败或内容不是有效凭证时返回 `None`。`#` 开头行与空行跳过，取第一行有效内容
- **参数：** 无
- **返回值：** `Optional[str]` — 有效凭证明文，或 `None`
- **注意：** 仅限本机内部使用；HTTP / 上层接口不得回传明文
- **举例：**

```python
token = Membership.read()
```

#### status

`Membership.status() -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 凭证状态摘要；不回传明文，可安全暴露给 HTTP 层
- **参数：** 无
- **返回值：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `configured` | `bool` | 存在有效凭证 |
| `invalid` | `bool` | 文件存在但内容不是有效凭证 |
| `path` | `str` | 相对路径 `userspace/system/membership/membership_token.txt` |

- **举例：**

```python
status = Membership.status()
if status["invalid"]:
    ...
```

#### save

`Membership.save(token: str) -> Optional[str]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 校验并写入凭证（写后 `chmod 0600`）；格式不对时不写文件
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `token` | `str` | 通用凭证；须匹配 `ntq_` + 48 位小写十六进制，首尾空白会去除 |

- **返回值：** `Optional[str]` — 成功返回 `None`；格式不对返回错误文案（可直接展示给用户）
- **举例：**

```python
err = Membership.save("ntq_" + "0" * 48)
assert err is None
```

#### clear

`Membership.clear() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 删除凭证文件；文件不存在时 no-op
- **参数：** 无
- **返回值：** `None`
- **举例：**

```python
Membership.clear()
```
