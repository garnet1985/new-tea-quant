from __future__ import annotations

from core.infra.setup.core import pip_index as pi
from core.infra.utils import Utils


def test_pip_index_delegates_to_utils_pkg() -> None:
    assert pi.TSINGHUA_SIMPLE == Utils.pkg.PYPI_MIRROR
    assert pi.TSINGHUA_HOST == Utils.pkg.PYPI_MIRROR_HOST
    assert callable(pi.use_china_mirror)
    assert callable(pi.pip_net_flags)
    assert callable(pi.announce_pip_index)
    assert pi.use_china_mirror() == Utils.pkg.use_china_mirror()
    assert pi.pip_net_flags() == Utils.pkg.pip_args()
