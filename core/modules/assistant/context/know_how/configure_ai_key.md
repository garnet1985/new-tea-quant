---
title: configure AI key 配置助理密钥
aliases:
  - api key
  - api-key
  - assistant
  - 密钥
  - API Key
  - AI 助理
  - 智谱
summary: 在设置 → AI 助理粘贴供应商密钥；页面不回读明文。
---

# 如何配置 AI Key

> 更完整的图文指南见官网：[配置 AI 助理](https://new-tea.cn/zh-hans/setup-AI)

聊天助理走本机已发现的供应商（OpenAI 兼容接口）。没有密钥时只能看界面，不能真正对话。

## 前置条件

- 已安装并打开 UI
- `userspace/extensions/assistant/providers/<id>/` 里已有 `config.py`（安装包一般会带至少一个供应商）

## 步骤

1. 打开 **设置 → AI 助理**
2. 列表里每个供应商会显示模型名、是否已配置密钥、是否启用
3. 在 **API Key** 框粘贴密钥（输入框是密码形态）
4. 点 **保存**
5. 成功后提示「已保存 … 的 API Key」，状态变成「已配置 API Key」；输入框会清空（本来就不会把旧密钥读回来）

之后用右下角助理入口对话即可。

## 验证

- 设置页显示「已配置 API Key」，**不会**显示密钥正文
- 发一句短问题能收到回复
- 密钥文件在对应供应商目录的 `api_key.txt`（权限应较严），不要提交到 git

## 常见坑

- **还没有发现供应商**：需要先有 `userspace/extensions/assistant/providers/<id>/config.py`。设置页会提示这一点。
- **供应商已禁用**：列表会标「已禁用」，先启用配置再聊。
- **不要把密钥贴进策略代码或对话记录里让助手「记住」。** 只走设置页。
- 打包 / 分发 userspace 时会剥离密钥；换机器要重新粘贴。

助手不能替你改文件或跑命令，只能根据注入的说明书和你贴出来的配置/报告回答。
