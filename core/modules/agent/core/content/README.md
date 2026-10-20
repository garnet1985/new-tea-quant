# content/ — 给模型与说明书读者看的文案（md / txt / allowlist）

**禁止**在这里放 Python。读取由 `code/executor/shared/prompt_loader.py` 与 `guider/docs.py` 完成。

| 目录 | 含义 |
|------|------|
| `global/` | 任何事都要：`whoiam`、`responsibility`、`redlines`、会话前缀 |
| `specific/navigator/` | 分流 classifier + advice 固定回复 |
| `specific/guider/` | 介绍者 system / nudges / allowlist / 回答风格 |
| `specific/worker/` | 执行者 system / nudges |
| `specific/present/` | present 阶段：把 work 结论按 scenario 模版改版式 |
| `ntq_wiki/` | NTQ 知识（`wiki/` 概念、`know_how/` **如何得到结果**）；默认只经 guider allowlist 注入，**不**整包灌进 worker |
| `templates/` | **如何呈现结果**：一 scenario 一模版；registry 在 `code/conf` 的 `PRESENTATION_SCENARIOS`，命中规则在 `code/executor/shared/present.py` |

链路：`ask → work* → present?`。无匹配 scenario 则透传 work 结论。

占位符 `{{identity}}`、`{{tools}}`、`{{scenario}}`、`{{template}}`、`{{conclusion}}` 等由 loader 注入。`{{identity}}` = redlines + responsibility 的能做/不做。多节文件用 `## section_key`。
