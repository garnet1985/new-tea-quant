@dataclass
class BaseDataContract:
    """Base data contract class."""

    data_key: str = None
    is_loaded: bool = False
    type: str = None

    # def __init__(self, data_key: str):
        

    # def info(self, data_key: DataKey) -> ContractInfo:
    #     """Get contract info for a data key."""
    #     pass