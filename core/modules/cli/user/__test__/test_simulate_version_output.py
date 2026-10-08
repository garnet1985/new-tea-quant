"""CLI simulate 输出 version_id（磁盘 layout 契约）。"""

from __future__ import annotations

from core.modules.cli.user.handlers import UserHandlers


def test_print_simulate_version_from_step_and_top_level(capsys):
    UserHandlers._print_simulate_version(
        {
            "version_id": "3",
            "enum": {
                "version_id": "3",
                "output_dir": "/tmp/demo/results/simulations/3/enum",
                "success": True,
            },
        },
        "enum",
    )
    out = capsys.readouterr().out
    assert "version_id: 3" in out
    assert "simulations/3/enum" in out


def test_print_simulate_version_step_only():
    UserHandlers._print_simulate_version(
        {
            "price": {
                "version_id": "5",
                "output_dir": "/x/simulations/5/price",
            }
        },
        "price",
    )


def test_print_simulate_version_ignores_non_dict():
    UserHandlers._print_simulate_version([], "enum")
