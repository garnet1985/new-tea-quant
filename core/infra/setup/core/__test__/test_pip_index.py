from __future__ import annotations

from core.infra.setup.core import pip_index as pi
from core.infra.utils import Utils


def test_pip_index_delegates_to_utils_pkg() -> None:
    assert pi.use_china_mirror is Utils.pkg.use_china_mirror
    assert pi.pip_net_flags is Utils.pkg.pip_args
    assert pi.announce_pip_index is Utils.pkg.announce
    assert pi.TSINGHUA_SIMPLE == Utils.pkg.PYPI_MIRROR
