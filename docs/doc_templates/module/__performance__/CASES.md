# 性能测试用例 — `<Module Display Name>`

**模块：** `<namespace.module_name>`  
**覆盖版本：** `<module.version>`  
**位置：** `__performance__/`

---

## Scope

`<本性能套件验证什么。>`

## 边界

**In scope**

- `<本模块公开路径上的性能指标>`

**Out of scope**

- `<跨模块 e2e（→ devtools/performance）；功能正确性（→ __test__）>`

---

## 输入（inputs/）

| 名称 | 路径或生成方式 | 说明 |
|------|----------------|------|
| `<input_id>` | `inputs/<…>` 或 `scripts/gen_*.py` + checksum | `<规模 / 约束>` |

---

## Scenario：`<场景短名>`

| 项 | 内容 |
|----|------|
| **目的** | `<测什么>` |
| **脚本** | `scripts/<name>.py` |
| **输入** | `<input_id 或路径>` |
| **结果目录** | `results/<module.version>/<scenario>/` |
| **关注指标** | `<wall_time、rows/s、peak_rss 等>` |
| **通过直觉** | `<相对基线 / 仅归档对比>` |

### 运行

```bash
python <module_path>/__performance__/scripts/<name>.py
```

---

## 结果与版本对比

- 发布或重大性能改动：写入 `results/<module.version>/`（基线可提交）。
- 本地试跑：`results/_local/`（建议 gitignore）。
