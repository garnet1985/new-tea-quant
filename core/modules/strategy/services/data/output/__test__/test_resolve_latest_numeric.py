"""``latest`` 须按数字 id 取最大目录，而非字典序（``\"9\" > \"20\"``）。"""

from pathlib import Path

from core.modules.strategy.services.data.output.version_manager import (
    StrategyOutputVersionService,
    _pick_latest_numeric_version_dir,
)


def test_pick_latest_numeric_version_dir():
    dirs = [Path(str(n)) for n in (1, 9, 10, 20, 19)]
    assert _pick_latest_numeric_version_dir(dirs).name == "20"


def test_resolve_enumerator_latest_uses_numeric_max(enum_simulation_root):
    version_dir, _ = StrategyOutputVersionService.resolve_enumerator_version(
        "unit_test_strategy", "latest"
    )
    assert int(version_dir.name) >= 20
