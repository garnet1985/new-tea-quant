# prompts/ — 给模型看的文案（md only）

- **禁止**在 `core/` 里堆大段中文 system / nudge / 固定回复。
- **禁止**在本目录用 `.py` 常量存文案。
- 占位符：`{{identity}}`、`{{tools}}` 等由 `core/prompt_store.load_prompt(..., variables=...)` 注入。
- 多节文件用 `## section_key`，经 `load_reply` / `load_nudge` 读取。

| 路径 | 用途 |
|------|------|
| `common/identity.md` | 产品身份与投资红线 |
| `common/session_preamble.md` | 会话状态前缀 |
| `navigate/classifier.md` | 本地分流器 system |
| `guide/arch.md` / `arch_user.md` / `wiki.md` | 介绍者 |
| `worker/system.md` | 执行者 |
| `nudges/*.md` | 纠错续写 |
| `replies.md` | 本地固定回复（不打模型） |
