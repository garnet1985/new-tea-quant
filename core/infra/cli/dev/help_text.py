"""Dev CLI command reference (``devcli.py -h`` epilog)."""

from __future__ import annotations

DEVCLI_COMMAND_REFERENCE = """
规则:  xx=命令  -v=版本  --xx=对象参数

  python devcli.py                         显示版本和帮助（默认）  同 -v / --version / -h
  python devcli.py ui                      启动 UI（launcher -d）
  python devcli.py uk                      结束 UI 端口（8000 + 8888）  同 ui_kill [--ntq-only]
  python devcli.py ic                      import 冒烟       同 check_import
  python devcli.py cgc                     清 .ntq           同 clear_global_cache
  python devcli.py csc                     清策略模拟缓存    同 clear_strategy_cache
  python devcli.py cdc                     清 DB 快照        同 cache_clear_db
  python devcli.py cmc                     清 results/       同 cache_clear_disk
  python devcli.py dbc                     DuckDB WAL        同 db_checkpoint [--recover]
  python devcli.py ex                      演示数据 zip      同 data_export_init
  python devcli.py pu                      打包 userspace    同 userspace_package [--no-zip]
  python devcli.py p -core_v0.3.2          发布检查          同 pack --version 0.3.2
  python devcli.py ssp 500                 分层样本池        同 sample_stock_pool N
  python devcli.py pc                      取消样本池        同 pool_clear
  python devcli.py cd                      依赖安装风险检测  同 check_deps [--verbose]
  python devcli.py bpe                     entity 性能基准（三档；默认 duckdb）
  python devcli.py bps                     slice 性能基准（三档；默认 duckdb）
  python devcli.py bpe --db mysql          entity + MySQL
  python devcli.py bps --db pgsql          slice + PostgreSQL
  python devcli.py bpc                     清理 BE 性能临时库 + test_strategies/*/results

  --verbose                                详细日志

  例: python devcli.py p -core_v0.3.2 --check-only
      同 python devcli.py pack --version 0.3.2 --check-only
      python devcli.py bpe
      python devcli.py bps --db mysql
      python devcli.py bpe --db pgsql
      python devcli.py bpc
""".strip()
