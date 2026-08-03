# Backtest Engine — 性能测试（`__performance__/`）

**模块：** `modules.backtest_engine`  
**用途：** 合成数据上的墙钟基线。  
**默认路径：** Strategy 枚举（`scripts/strategies/perf_null` → `EnumeratorPipeline` → BE `entity_based` / `slice_based`）。  
另提供 idle（空 `on_tick`）作调度下限。手搓 `io_*` 仍可通过 `--case` 调用，不推荐作默认。

报告模板：[`docs/doc_templates/module/__performance__/REPORT_TEMPLATE.md`](../../../../docs/doc_templates/module/__performance__/REPORT_TEMPLATE.md)。

## 目录

```text
__performance__/
├── README.md
├── CASES.md
├── fake_data/                         # 生成的 CSV（gitignore）
├── scripts/
│   ├── data_gen.py                    # 1. 生成合成数据
│   ├── db_creation.py                 # 2. 建临时库并导入
│   ├── test_script.py                 # 3. 跑 cases（默认 entity+slice enum）
│   ├── clean_up.py                    # 4. 清理
│   ├── workload.py                    # worker overlay / idle·io callbacks
│   └── strategies/perf_null/          # 测试用 null 策略（脚本一部分）
├── .workdir/                          # DuckDB 文件 + db_registry.json（gitignore）
└── results/_local/                    # 本地试跑报告（gitignore）
```

**约定：** 生成物不离开本 `__performance__/`。DuckDB 文件名 `perf_test_tmp`，冲突则 `perf_test_tmp_1`…  
清理只删 registry 中、且名称匹配 `perf_test_tmp*` 的库。

## Fake DB 切换（进程内，不改 userspace 配置）

套件**不**改写 `userspace` 里的数据库配置文件；只在**当前 Python 进程**里把默认 DB / DataManager 指到 `.workdir` 临时库：

1. **建库**（`db_creation.py`）：在 `__performance__/.workdir/` 写出 `perf_test_tmp*.duckdb`（data/tag/strategy 三域），登记到 `db_registry.json`。
2. **主进程挂载**（`test_script._attach_perf_duckdb`）：
   - `Db.duckdb.overlay_domain_paths(data=…, tag=…, strategy=…)` 生成一份 **内存中的** database 配置（绝对路径指向 `.workdir`）
   - `Db.manager.reset_default()` → `create(cfg)` → `set_default(db)`
   - `DataManager.reset_instance()` 后用该 `db` 新建实例  
   → 此后本进程的 `DataManager` / ContractIssuer 读的是 fake DuckDB，而不是 ProjectContext 里的 MySQL/业务库。
3. **Worker 挂载**（`workload.install_perf_worker_db_overlay`）：
   - 同样 overlay 配置写入环境变量 `NTQ_DUCKDB_CONFIG_JSON`（spawn 子进程可继承）
   - 并 monkeypatch `database_config_read_only`，让 ProcessPool worker 的 RO 连接也指向 fake 库
4. **ProcessPool 放锁**：池开跑前 `release` 主进程 DuckDB 句柄；子进程 RO 打开；池结束后按默认逻辑 `resume`（会按 ProjectContext 再连——见下）。
5. **还原**：
   - **没有**把 ProjectContext / userspace 配置写回磁盘——本来就没改文件
   - 进程退出后，内存里的 overlay / env / monkeypatch 全部消失
   - 若同进程还要继续跑业务库：需自行 `DataManager.reset_instance()` + 按 ProjectContext 重建 `Db.manager`（当前 `be_perf` / `test_script` 跑完即退出，不做二次还原）
   - 磁盘上的 `.workdir` 临时库保留以便复用；要删用 `be_perf_clear` / `clean_up.py --all`

## 工作量

| 套件 | 行为 | 何时用 |
|------|------|--------|
| **strategy_enum_***（默认） | null 策略 + EnumeratorPipeline（entity + slice） | 接近实战 BE 栈 |
| **idle_*** | `on_tick` noop | 调度/timeline 下限 |
| **io_***（非默认） | 手搓 `load_batch` + as-of | 遗留对比 |

运行时读 **DuckDB**（不读 CSV）。CSV 仅用于 gen/import。

## 如何运行

```bash
python devcli.py be_perf
python devcli.py be_perf --idle
python devcli.py be_perf_clear
# 缩写: bp / bpc
```

```bash
python core/modules/backtest_engine/__performance__/scripts/data_gen.py
python core/modules/backtest_engine/__performance__/scripts/db_creation.py --reuse

# 默认 entity + slice enum
python core/modules/backtest_engine/__performance__/scripts/test_script.py
python core/modules/backtest_engine/__performance__/scripts/test_script.py --case strategy_enum_entity
python core/modules/backtest_engine/__performance__/scripts/test_script.py --case strategy_enum_slice

python core/modules/backtest_engine/__performance__/scripts/test_script.py --idle
python core/modules/backtest_engine/__performance__/scripts/clean_up.py --all
```

实验默认规模见 [`scripts/config.py`](./scripts/config.py)（当前小流量：10 股 × 2024）。
