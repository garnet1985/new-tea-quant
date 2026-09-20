# 助理百科（给模型读）

**版本：** `0.1.0`

把 markdown 放进下面三个目录即可，保存后下次对话会自动扫到。不要放模块根 `README.md`。

```text
context/
  global/      # 每次对话都带上，写短
  wiki/        # 概念 / 介绍
  know_how/    # 操作步骤
```

文首可选：

```yaml
---
title: 配置策略 settings
aliases: [settings.py, goal, 止盈止损]
summary: 一句话，给调度挑选文档用
---
```

没有文首时，用第一个 `# 标题` 或文件名。`doc_id` = `分类/相对路径去后缀`，例如 `know_how/config_strategy_settings`。

子目录也会扫到，例如 `wiki/strategy/strategy_decision.md` → `wiki/strategy/strategy_decision`。

调度：`global` 每次附上。`wiki` 与 `know_how` 较少时整包附上；多了会先让模型按目录挑选最多 3 篇，失败则按标题/别名关键词挑。挑中的正文优先写入提示，避免 `global` 把字数预算占满。`global` 请保持短篇；长参考放到 `wiki` / `know_how`。

对 NTQ 用户说话。不要写 Facade / BFF / 类名。
