# Agent — 用户指南

**模块：** `modules.agent` · **版本：** `0.1.0`

**最低支持核心版本：** `>=0.6.0`

`Agent 是 NTQ 的 AI 助手——你跟它说想干嘛，它后台调工具帮你写策略、读报告、跑扫描。`  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 用大白话提需求，让 Agent 帮你新建一个空策略文件
- 实现新策略或首次回测前，Agent 会先给出「测试计划」（止损/止盈/区间等敏感设定）请你确认，再说「执行」才动手
- 新建或改特征标签前，Agent 会先给出「特征标签计划」（算什么、算哪些、怎么更新等）请你确认，再说「执行」才动手
- 让 Agent 读回测报告，帮你总结盈亏、持仓变化，并可选引出资金模拟 / 止盈止损对照 / 多时段对照等下一步
- 让 Agent 帮你跑全市场扫描，找出策略能抓到的机会
- 让 Agent 创建/计算特征标签，并读标签报告
- （少用）探查本机表/契约/数据新鲜度，或在 userspace 建自定义表（不改 `core/tables`）
- 查看它手头有哪些工具可用、清空本机会话、调整偏好

## 配置说明

在哪配、配什么、默认值是什么：

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| `base_url` | `userspace/system/config/membership.json` | 由会员凭证文件决定 | 使用 NTQ 官网服务时的根地址，一般不需要改 |
| Provider | `python cli.py a --set-provider <名字>` | `ntq` | 用 NTQ 官方模型，还是切到自己准备的渠道 |
| 跨会话偏好 | `python cli.py a --remember "回答简短"` | 无 | 让 Agent 记住你的口味，下次自动沿用 |

如果想完全用自己本机的模型开发自测，可以设环境变量 `NTQ_AGENT_OWN_KEYS=1`。

## 常见使用方式

### 场景 1：先问问 Agent 能干啥

1. 打开终端，切到仓库根目录
2. 跑 `python cli.py a --tools` 查看 Agent 手头有哪些工具
3. 跑 `python cli.py a "NTQ 是什么"` 试一句，看看回复顺不顺眼

### 场景 2：新建策略并回测（先确认测试计划）

1. 确认 `userspace/strategies/_template/empty_strategy/` 这个模板目录还在
2. 跑 `python cli.py a "帮我做一个 20 日均线金叉策略并回测"`
3. Agent 先回复「测试计划」（目标、止盈止损、区间等），等你改设定或说「执行」
4. 你确认执行后，它才写文件、跑机会盘点与价格回测并报告；报告末尾可能问下一步（资金模拟 / 止盈止损对照 / 多时段对照）。做资金模拟前会再给你一份「资金模拟计划」（本金、持仓上限、分配方式等）确认
5. 若只要空骨架，可以说「只建一个叫 macd_cross 的空策略」；目录已存在时它会拒绝覆盖

### 场景 3：让它读回测报告

1. 先跑过一次回测，确认报告已生成
2. 跑 `python cli.py a "总结一下最近一次回测的盈亏和持仓"`
3. Agent 会去翻报告，用人话总结给你

### 场景 4：新建特征标签并计算（先确认特征标签计划）

1. 确认 `userspace/extensions/tags/_template/empty_scenario/` 模板还在
2. 跑 `python cli.py a "帮我做一个按市值分大中小盘的特征标签并计算"`
3. Agent 先回复「特征标签计划」（算什么、算哪些、怎么更新等），等你改设定或说「执行」
4. 你确认后，它才写 `tag.py` / `settings.py`、校验、跑标签计算并读报告

### 场景 5：清空会话、调整偏好

1. 跑 `python cli.py a --clear` 清空本机会话  
2. 跑 `python cli.py a --prefs` 查看跨会话偏好  
3. 跑 `python cli.py a --remember "回答简短"` 让它记住偏好  
4. 跑 `python cli.py a --settings` 查看默认 Provider 等配置

## 常见坑与注意事项

- **新建策略提示失败**：先检查模板目录 `userspace/strategies/_template/empty_strategy/` 是否还在，缺了 Agent 无法复制骨架
- **目标策略目录已存在**：Agent 不会自动覆盖，先手动删掉旧目录或换个名字再让它建
- **改了 `base_url` 没生效**：只认 `userspace/system/config/membership.json` 里的地址，其它地方改了不算数
- **想用自己本机的模型自测**：要显式设 `NTQ_AGENT_OWN_KEYS=1`，否则默认走 NTQ 官方渠道
- **回复风格不对**：先用 `--remember` 或 `--prefs` 调好偏好，不要在每次对话里重复叮嘱

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
