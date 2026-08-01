# <Module Display Name>（`<namespace.module_name>`）

<!-- 例：Database（`infra.db`）、Project Context（`infra.project_context`） -->

`<一句话模块职责。写「做什么」，不写实现细节。缩写 / 生僻英文首次出现括注，或指向 glossary.yaml（如 NTQ＝New Tea Quant；Facade＝门面）。>`

## 适用场景

- `<场景 1：谁在什么情况下会用到>`
- `<场景 2>`
- `<场景 3>`

## 模块依赖

<!-- 仅列 module_info.yaml 的 dependencies；无依赖写「无」。不要贴 import / 代码。 -->

- `<dep.name>`：`<用途一句话>`

## 设计初衷（可选，保持简短）

- **要解决的问题：** `<1～2 句；细节放 docs/DESIGN 或 docs/CONCEPTS>`
- **明确不做：** `<可选；边界一句话>`

## 常见问题（可选）

**Q：`<问题>`**  
A：`<简短文字；原理 → docs/CONCEPTS；上手 → QUICKSTART；调用 → API.md；名词 → glossary.yaml>`

## 相关文档

<!-- 不需要的可选文档删掉对应行 -->
- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [概念与运作](./docs/CONCEPTS.md)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
- [性能测试](./__performance__/CASES.md)

---

## 填写约定（copy 整棵 module/ 骨架后可删本段）

1. **纯文字**；代码与上手不在本文件。
2. 不需要的可选文档（QUICKSTART / CONCEPTS / DESIGN / `__performance__`）整文件删除，并去掉本表链接。
