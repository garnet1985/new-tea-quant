# 文档模板（`docs/doc_templates/`）

全局可 copy 模板。模块级骨架在 [`module/`](module/)——**目录结构与真实模块一致**，新模块整棵 copy 后改 `<占位>` 即可。

**文档 SSOT：** [`module-doc-standard.md`](../module-doc-standard.md)  
**模块规则：** [`CORE_MODULE_STANDARDS.md`](../../CORE_MODULE_STANDARDS.md)

## 用法

```bash
# 例：新建 modules/foo
cp -R docs/doc_templates/module/ modules/foo/
# 然后：替换 <占位>；不需要的可选文件/目录整份删除（并去掉 README 里对应链接）
```

可选可删：`QUICKSTART.md`、`docs/CONCEPTS.md`、`docs/DESIGN.md`、整个 `__performance__/`。  
`docs/notes/` 仅自用草稿，无正式契约。

## 放置规则

| 位置 | 文档 |
|------|------|
| **模块根**（有则必须在此） | `README.md`、`API.md`、`QUICKSTART.md`（可选）、`glossary.yaml`、`module_info.yaml` |
| **`docs/`**（标准文档） | `ARCHITECTURE.md`、`DESIGN.md`（可选）、`CONCEPTS.md`（可选） |
| **`docs/notes/`** | 临时 / 开发者自用；无模板、非正式契约 |
| **`__test__/`** | `TEST_CASES.md` + `test_api.py`（必须） |
| **`__performance__/`**（可选） | 正式本模块 bench：`README` / `CASES` / `inputs` / `scripts` / `results/<version>/` |

## 测试与性能（摘要）

| 位置 | 内容 |
|------|------|
| `<module>/__test__/` | **必须** `test_api.py` + `TEST_CASES.md`；可选 integration、**短** performance 冒烟 |
| `<package>/__test__/` | 该包 unit + `TEST_CASES.md`（可从模块根 `__test__/TEST_CASES.md` 再 copy 一份改 Scope） |
| `<module>/__performance__/` | 正式单模块 bench（固定输入、脚本、按版本结果、CASES）；跨模块用 `devcli.py bpe/bps` |

默认 CI 跑 `__test__/`；`__performance__/` 手动或 nightly。

## 骨架对照

```text
docs/doc_templates/module/
├── README.md
├── API.md
├── QUICKSTART.md              # 可选
├── glossary.yaml
├── module_info.yaml
├── __test__/
│   ├── TEST_CASES.md
│   └── test_api.py
├── __performance__/           # 可选整目录删除
│   ├── README.md
│   ├── CASES.md
│   ├── inputs/  scripts/  results/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md              # 可选
    ├── CONCEPTS.md            # 可选
    └── notes/
```

## 定稿状态

| 文件 | 状态 |
|------|------|
| `README.md` / `API.md` / `glossary.yaml` / `module_info.yaml` | 已定稿（v1） |
| `QUICKSTART.md` / `docs/CONCEPTS.md` / `docs/DESIGN.md` | 已定稿（v1，可选） |
| `docs/ARCHITECTURE.md` | 已定稿（v1） |
| `__test__/TEST_CASES.md` + `test_api.py` | 已定稿（v1） |
| `__performance__/README.md` + `CASES.md` | 已定稿（v1，框架）；指标细表可后补 |
