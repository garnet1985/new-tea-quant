from core.modules.strategy_legacy.engines.simulator.price_factor.session_roi_stats import is_forced_exit_investment


@dataclass
class DiscoveredContracts:
    """Discovered contracts class."""
    is_discovered: bool = False
    available_keys: List[str] = field(default_factory=list)
    contracts: Dict[str, ContractMeta] = field(default_factory=dict)


    def __init__(self):
        self.discover()


    def list_all(self) -> List[ContractMeta]:
        """List all contracts."""
        return self.contracts

    def list_all_keys(self) -> List[str]:
        """List all contract keys."""
        return [contract.key for contract in self.contracts]

    def is_defined(self, data_key: str) -> bool:
        """Check if contract is defined."""
        return data_key in self.list_all_keys()

    def discover(self):
        """Discover contracts."""
        customed = self.discover_customized()
        default = self.discover_defaults()
        self.contracts = self.merge(customed, default)
        self.available_keys = list(self.contracts.keys())
        # TODO: add discover logic

    def discover_customized(self):
        """Discover contracts."""
        self.is_discovered = True
        # TODO: add discover logic


    def discover_defaults(self):
        """Discover default contracts."""
        self.is_discovered = True
        # TODO: add discover logic

    def merge(self, other: "DiscoveredContracts"):
        """Merge other contracts into this."""
        self.contracts.extend(other.contracts)
        self.is_discovered = True
        self.contracts = list(set(self.contracts))

    def is_valid(self) -> bool:
        """Check if contracts are valid."""
        # TODO: add discover logic