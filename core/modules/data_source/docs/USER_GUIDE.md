# Data Source — 用户指南

**模块：** `modules.data_source` · **版本：** `0.4.0`

**最低支持核心版本：** `>=0.5.0`

`DataSource 对接外部数据源（Tushare、Yahoo 等），把数据拉下来存进本地数据库。`
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 一键从外部数据源（默认 Tushare）抓全量历史：股票列表、K 线、行业、指数、宏观
- 每日增量更新：只抓"上次抓到之后"的新数据，不重复拉历史
- 限流和重试内置：按各 Provider 的限速自动排队，失败的任务下次接着补
- 抓取状态落盘：每次运行写一份 `status.json`，UI 任务栏直接看进度
- 想接新数据源（Wind、东财等）只需新增 Provider 和 Handler，不动主流程

## 配置说明

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| Tushare token | `userspace/extensions/data_source/providers/tushare/auth_token.txt`，或环境变量 `TUSHARE_TOKEN` | 无 | 必填。token 从 [tushare.pro](https://tushare.pro) 个人页拿 |
| 各数据源的启用开关、目标表 | `userspace/extensions/data_source/handlers/<name>/settings.py` 里的 `settings` | 全部已启用 | 关掉某个数据源就把对应 entry 禁用 |
| 数据源列表（哪些 key 存在） | `userspace/data_source/mapping.py` 的 `DATA_SOURCES` | 系统默认 | 一般不用动；新增数据源时登记 |
| 抓取样本股票池 | `data.json` 的 `use_sample_stock_list` | `null` | 设为整数则只抓 / 只保留这么多只样本股，开发期省时间 |

## 常见使用方式

### 场景 1：首次跑 NTQ，把数据拉下来

1. 在 [tushare.pro](https://tushare.pro) 注册并拿到自己的 token。
2. 把 token 写到 `userspace/extensions/data_source/providers/tushare/auth_token.txt`（一行，就是 token 字符串），或设环境变量 `TUSHARE_TOKEN`。
3. 跑 `python cli.py renew`。不传参数 = 抓全部已启用的数据源。
4. 等待抓完。状态会写到 `status.json`，UI 任务栏能实时看进度。
5. 抓完后用 `python cli.py list tables` 确认表都在。

### 场景 2：每日增量更新

1. 直接跑 `python cli.py renew`。
2. 系统会比对"本地最新数据日期"和"真实世界最近交易日"，只抓增量。
3. 失败的任务本次跳过，下次 renew 自动接着补。
4. 想强制重拉某张表的全部历史：`python cli.py renew <表名或数据源 key> --force`。

### 场景 3：只更新某一张表

1. 跑 `python cli.py renew list --json` 看有哪些可抓的目标。
2. 挑一个表名或 key，例如 `python cli.py renew sys_data_stock_klines`。
3. 只更新它，其他数据源不动。

### 场景 4：清理运行日志

1. 跑 `python cli.py renew --clear-logs`。
2. 已结束的运行目录会被清掉，进行中的不动。

### 场景 5：接一个新的数据源

1. 在 `userspace/data_source/providers/` 下加一个 Provider（继承框架约定）。
2. 在 `userspace/data_source/handlers/<name>/` 下加 Handler 和 `settings.py`。
3. 在 `userspace/data_source/mapping.py` 的 `DATA_SOURCES` 里登记一行。
4. 重启进程后即可用 `renew <新 key>` 抓它。

## 常见坑与注意事项

- **没配 token 直接 renew，全部失败：** 现象是所有 Tushare 任务都报"未授权"。解决：写 `auth_token.txt` 或设 `TUSHARE_TOKEN` 环境变量后重跑。
- **Tushare 积分不够，部分接口一直 401 / 权限不足：** Tushare 按积分分级，一些接口（如每日指标、行业分类）要更高积分。解决：升级积分，或在 handler 的 `settings.py` 里把需要高积分的源关掉。
- **触发限流被卡住：** Tushare 单 token 一般 500 次/分钟；超出会等一个窗口再试。这是预期行为，不要连续 Ctrl+C 重启——进度会丢。
- **抓取中途进程被杀（OOM / 手动停）：** 已写入的数据不会丢，下次 renew 会从"每只股票的本地最新日期"接着抓。`status.json` 里能看到上次哪些任务没完成。
- **`renew --force` 慎用：** 它会无视已有缓存从默认起点重拉，全市场可能要几小时。仅当你怀疑数据被污染时再用。

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
