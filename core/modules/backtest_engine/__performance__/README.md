# Backtest Engine — 性能测试（`__performance__/`）

**模块：** `modules.backtest_engine`  
**用途：** entity_based / slice_based 调度空转基线（合成数据）。  
strategy / tag **不再**单独做 performance：应用层开销叠在 BE 之上，引擎准则以本目录为准。

报告模板：[`docs/doc_templates/module/__performance__/REPORT_TEMPLATE.md`](../../../../docs/doc_templates/module/__performance__/REPORT_TEMPLATE.md)。

## 目录

```text
__performance__/
├── README.md
├── CASES.md
├── fake_data/          # 生成的 CSV（gitignore）
├── scripts/
│   ├── data_gen.py     # 1. 生成合成数据
│   ├── db_creation.py  # 2. 建临时库并导入
│   ├── test_script.py  # 3. 跑 idle cases
│   └── clean_up.py     # 4. 清理（可单独调用以便复用）
├── .workdir/           # DuckDB 文件 + db_registry.json（gitignore）
└── results/_local/     # 本地试跑报告（gitignore）
```

**约定：** 生成物不离开本 `__performance__/`。DuckDB 文件名 `perf_test_tmp`，冲突则 `perf_test_tmp_1`…  
清理只删 registry 中、且名称匹配 `perf_test_tmp*` 的库。

## 输入策略

| 情况 | 做法 |
|------|------|
| 本套件 | `data_gen.py` 合成（不要求行情真实，要求脚本稳定：seed/规模/日期窗） |
| 大样本 | 仍用生成器；CSV/DB 不进 git |

实验默认规模见 [`scripts/config.py`](./scripts/config.py)（`DEFAULT_STOCK_COUNT` / 日期窗 / seed）。

## 引擎选择

- **默认 DuckDB**（`--db duckdb`）：库文件在 `.workdir/`。
- 显式 `--db mysql|pgsql`：服务器上建 `perf_test_tmp[_N]`（当前实验 pass 仅 stub；必须走 registry）。
- **不**静默跟随用户当前业务库配置。

DuckDB 路径覆盖：`Db.duckdb.overlay_domain_paths(...)`（绝对路径指向 `.workdir/`）。

## 如何运行

推荐（DevCLI；默认 `--db duckdb`）：

```bash
python devcli.py be_perf
python devcli.py be_perf --db duckdb --with-io
python devcli.py be_perf_clear
# 缩写: bp / bpc
```

等价脚本（仓库根目录）：

```bash
# 1) 生成 fake_data
python core/modules/backtest_engine/__performance__/scripts/data_gen.py

# 2) 导入临时 DuckDB（可 --reuse 复用已有库）
python core/modules/backtest_engine/__performance__/scripts/db_creation.py

# 3) 跑 idle（需已 import；on_tick 空转测调度）
#    --with-io：主进程预读日 K（entity worker 无法再开同一 DuckDB 文件锁）
python core/modules/backtest_engine/__performance__/scripts/test_script.py
python core/modules/backtest_engine/__performance__/scripts/test_script.py --with-io

# 4) 清理（按需；不跑 clean 即可复用数据/库）
python core/modules/backtest_engine/__performance__/scripts/clean_up.py --db
python core/modules/backtest_engine/__performance__/scripts/clean_up.py --data
python core/modules/backtest_engine/__performance__/scripts/clean_up.py --all
```

## 相关

- [CASES.md](./CASES.md)
- [../API.md](../API.md)
