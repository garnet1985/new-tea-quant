# `<Module Display Name>` — 性能测试（`__performance__/`）

<!--
  可选：无正式 bench 时删除整个 __performance__/ 目录。
  CI 短冒烟仍放 __test__/test_performance_*.py。
-->

**模块：** `<namespace.module_name>`  
**当前基线版本：** `<module.version>`

## 用途

`<1～3 句：本套件守哪类性能回归。>`

与 `__test__/` 的区别：这里是可版本对比的正式 bench（固定输入 + 脚本 + `results/<version>/`）。

## 目录

```text
__performance__/
├── README.md
├── CASES.md
├── inputs/
├── scripts/
└── results/<version>/
```

## 环境假设

| 项 | 说明 |
|----|------|
| 机器 / CPU | `<…>` |
| 内存 | `<…>` |
| 数据规模 | `<…>` |
| 其他 | `<…>` |

## 如何运行

```bash
python <module_path>/__performance__/scripts/<run_bench>.py
```

结果写入：`__performance__/results/<module.version>/`

## 相关

- [CASES.md](./CASES.md)
- [../API.md](../API.md)
- [../__test__/TEST_CASES.md](../__test__/TEST_CASES.md)
