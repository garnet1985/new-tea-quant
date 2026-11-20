# PostProcess — 用户指南

**模块：** `modules.post_process` · **版本：** `0.3.2`

**最低支持核心版本：** `>=0.5.0`

`PostProcess 管扫描完的机会怎么分发——发微信、发邮件、喂给本地 Broker 模拟下单。`  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 把策略扫描结果规成统一格式：哪只票、什么价位、哪条策略报的
- 自动发现并执行你配置的后处理（PostProcessor），一条后处理可挂多个 Adapter
- 内置示例 Adapter：微信机器人通知、邮件通知、短信通知、本地 Broker 模拟下单、终端展示
- 支持声明依赖（`depends_on`），默认各 Adapter 独立跑；有依赖时按拓扑序执行并注入 `deps`
- **启用是全局的**：每个策略扫描结束后，会跑全部 `is_enabled: true` 的方案（不进策略 settings）

## 配置说明

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| `key` / `is_enabled` / `on_error` / `on_empty` | `userspace/extensions/post_process/post_processors/<key>/post_processor.json` | 视示例 | 后处理声明：叫什么、是否启用、出错时怎么办、没机会时还跑不跑 |
| `adapters.<name>.config` / `depends_on` | 同上 | 视示例 | 挂哪些 Adapter、各自参数与依赖 |
| 各 Adapter 自己的 settings（`dry_run`、`webhook_url`、`to`、`engine` 等） | `userspace/extensions/post_process/adapters/<name>/settings.py` | `dry_run: True` 居多 | Adapter 行为细节；通知类大多默认只打印不真发 |

工作台：**高级功能 → 后续处理** 可查看 Adapter 目录、启用/禁用方案、编辑方案内 adapters 与 `depends_on`。策略选股页会展示当前已启用的全局方案。

## 常见使用方式

### 场景 1：配置微信通知（企业微信机器人）

1. 复制 `adapters/wechat_sender/token.example.txt` 为 `token.txt`，填入 webhook 地址；或设环境变量 `NTQ_WECOM_WEBHOOK`。
2. 在 `adapters/wechat_sender/settings.py` 里把 `dry_run` 改成 `False`。
3. 新建或编辑 `post_processors/<你的key>/post_processor.json`，把 `wechat_sender` 挂进 `adapters`，并设 `is_enabled: true`。
4. 跑一次扫描；每个策略扫完后，已启用的方案都会收到该策略的机会列表。

### 场景 2：配置邮件通知

1. 编辑 `adapters/email_sender/settings.py`：填收件人 `to`、发件人 `from_addr`，把 `dry_run` 改成 `False`。
2. 把 `email_sender` 挂到你的 post_processor.json，并启用该方案。
3. 触发扫描，邮箱收到标题形如 `[NTQ] 扫描完成（<日期>）· N 个机会` 的邮件。

### 场景 3：接本地 Broker 做模拟下单

1. 编辑 `adapters/demo_broker/settings.py`：选 `engine`（`easytrader` / `vnpy` / `qmt`），设默认下单数量或金额。
2. 先保持 `dry_run: True` 跑一遍，确认打印出来的下单意图正确。
3. 准备好对应引擎的账号配置后，再把 `dry_run` 关掉接真券商。
4. 把 `demo_broker` 挂进你的 post_processor，并启用该方案。

### 场景 4：自己写一个新 Adapter

1. 在 `adapters/` 下新建目录，写 `adapter.py`（继承 `BaseAdapter`，实现 `run`）。
2. 加 `settings.py` 放默认配置。
3. 在 post_processor.json 里挂上它（或在工作台「编辑步骤」里添加）。
4. 详见 [QUICKSTART.md](../QUICKSTART.md) 和 [POST_PROCESSOR.md](./POST_PROCESSOR.md)。

## 执行单元就绪（红 / 黄 / 绿）

工作台用 `status` 着色，优先级：**不可用 > 测试模式 > 可用**。

| status | 色 | remark |
|--------|----|--------|
| `unavailable` | 红 | 缺少 xxx 配置 / 无法加载 |
| `dry_run` | 黄 | 当前是测试模式（真发配置已齐，但仍 dry_run） |
| `live` | 绿 | 可以正常使用 |

- Adapter 声明真发必备项（`required_for_live` / `required_files` / `required_env`），或覆盖 `check_readiness`
- 未配 token/收件人/webhook 的通知类 → **红**（即使 settings 里 dry_run=true）
- `ntq_email`：本地不存 token/邮箱；用 `Membership.read()`，官网发往**注册邮箱**（终身 30 次）
- 查询：`PostProcess.check_adapter_readiness("email_sender")`

## 常见坑与注意事项

- **扫描完没反应**：对应方案 `is_enabled: false`，或目录下没有可用 PostProcessor。
- **以为下单/发消息了其实没有**：内置示例的 `dry_run` 默认是 `True`，只打印不执行。生产用记得显式改。
- **执行单元全红**：先确认 BFF 已加载本版本；再看悬停提示里的 readiness 原因。
- **密钥被提交到 git**：webhook、token、邮箱授权码别写死在 `settings.py`。优先用环境变量或同目录的 `token.txt`（已在 gitignore）。
- **指望 A Adapter 跑完再跑 B**：默认是无序集合，别依赖执行顺序。真有依赖要求，在 post_processor.json 里写 `depends_on`（工作台可编辑）。
- **机会格式不对直接被拒**：扫描结果会被规成三层协议（会话 / 单策略 / 机会），字段缺了会在校验阶段报错。细节见 [PROTOCOL.md](./PROTOCOL.md)。
- **不要再写策略 `scanner.post_process`**：该字段已废弃；加载时会被丢弃。

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
