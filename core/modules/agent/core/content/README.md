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
| `templates/` | **如何呈现结果**：一 scenario 一模版；registry 在 `PRESENTATION_SCENARIOS` |

链路：`ask → work* → present?`。无匹配 scenario 则透传 work 结论。

## 用户扩展（userspace，不在本目录）

路径：`userspace/extensions/agent/`（见 QUICKSTART）。

| 子目录 | 形式 | 规则 |
|--------|------|------|
| `tools/{name}/tool.py` | Python | 仅新增；与内置同名忽略 |
| `templates/{scenario}.md` | Markdown | 可覆盖内置正文；新 scenario 用 YAML frontmatter `match` |
| `prompts/{lane}.md` | Markdown | 仅追加（context/worker/guider/present）；冲突以产品为准 |

占位符 `{{identity}}`、`{{tools}}`、`{{scenario}}`、`{{template}}`、`{{conclusion}}` 等由 loader 注入。多节文件用 `## section_key`。
