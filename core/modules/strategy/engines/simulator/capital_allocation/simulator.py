#!/usr/bin/env python3
"""Capital allocation simulator bridge during migration."""

from core.modules.strategy1.components.simulator.capital_allocation.capital_allocation_simulator import (  # noqa: F401
    CapitalAllocationSimulator,
)
from core.modules.strategy1.components.simulator.capital_allocation.capital_allocation_simulator_config import (  # noqa: F401
    CapitalAllocationSimulatorConfig,
)

__all__ = [
    "CapitalAllocationSimulatorConfig",
    "CapitalAllocationSimulator",
]

