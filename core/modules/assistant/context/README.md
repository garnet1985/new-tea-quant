# 助理百科（给模型读，不是给人读的模块文档）

**版本：** `0.1.0`

这里放 NTQ 小百科。`chat` 之后会把词条喂给模型。现在还没接入，先把内容写对。

不要写进：

- 模块根 `glossary.yaml`（那是给开发者的名词：Facade、deep-import）
- `docs/`（给人看的架构 / 设计）
- `userspace/`（那是供应商配置和用户策略）

`core/context/` 也不要用：`core/` 只放 Python 实施层。

## 怎么加一条

1. 复制 `entries/_template.yaml` → `entries/<id>.yaml`
2. `<id>` 用小写英文 + 下划线，和文件名一致
3. 只填你有把握的；不确定就别写

## 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 与文件名相同 |
| `kind` | 是 | `term` 名词 / `principle` 原则 / `how_to` 怎么做 |
| `title` | 是 | 用户会问的那个名字 |
| `aliases` | 否 | 别名、UI 上的叫法 |
| `summary` | 是 | **2～4 句。** 以后默认塞进每次对话 |
| `body` | 否 | 稍细一点；以后按问题再检索。宁可短 |
| `avoid` | 否 | 模型容易说错的话，写成「不要说成…」 |
| `see_also` | 否 | 其它词条 `id` |

## 写法

- 对 **NTQ 用户** 说话，不要对开发者说话
- 用产品里的词：策略、Version、选股、报告、`has_opportunity`、`settings.py`
- 不要写实现细节：Facade、指纹算法、BFF、类名
- `summary` 单独成立；就算不读 `body` 也不能含糊
- 一条只讲一件事。又是名词又是教程就拆成 `term` + `how_to`

## 建议先写的

- 名词：NTQ、策略、Version、机会、选股、决策者
- 原则：先规则再代码、三步回测各自看什么
- 怎么做：新建策略、`has_opportunity` 返回什么、报告怎么读

两篇填好的例子：`entries/ntq.yaml`、`entries/has_opportunity.yaml`。
