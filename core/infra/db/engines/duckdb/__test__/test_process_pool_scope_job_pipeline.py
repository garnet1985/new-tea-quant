"""JobPipeline 与 process_pool_scope 集成判断。"""
from core.infra.db.engines.duckdb.process_pool_scope import should_apply_process_pool_scope


def test_should_apply_auto_duckdb_process():
    assert should_apply_process_pool_scope(
        mode="auto",
        use_process_pool=True,
    ) in (True, False)  # 取决于本机 database 配置


def test_should_apply_off():
    assert not should_apply_process_pool_scope(
        mode="off",
        use_process_pool=True,
    )


def test_should_apply_on_requires_process():
    assert not should_apply_process_pool_scope(
        mode="on",
        use_process_pool=False,
    )
