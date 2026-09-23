"""兼容路径。镜像策略只在 ``Utils.pkg``。"""
from core.infra.utils.core.pkg_index import PkgIndex

TSINGHUA_SIMPLE = PkgIndex.PYPI_MIRROR
TSINGHUA_HOST = PkgIndex.PYPI_MIRROR_HOST

use_china_mirror = PkgIndex.use_china_mirror
pip_net_flags = PkgIndex.pip_args
announce_pip_index = PkgIndex.announce
pip_network_hint = PkgIndex.pip_hint
reset_for_tests = PkgIndex.reset_for_tests
pypi_reachable = PkgIndex.pypi_reachable
parse_pkg_version = PkgIndex.parse_pkg_version
version_meets = PkgIndex.version_meets
installed_version = PkgIndex.installed_version
pip_meets_minimum = PkgIndex.pip_meets_minimum
