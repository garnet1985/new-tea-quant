class DataSourceConfig:
    """
    DataSource Config class
    """
    def __init__(self, data_source_name: str):
        self.data_source_name = data_source_name
        pass

    def _discover_config(self):
        """
        Discover the config
        """
        config_path = PathManager.data_source_config(self.data_source_name)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return ConfigManager.load_json(config_path)

    def _is_config_valid(self, raw_config: Dict[str, Any]):
        """
        Check if the config is valid
        """
        pass
        return True

    def _parse_config(self, raw_config: Dict[str, Any]):
        """
        Parse the config
        """
        self.mode = valid_config.get("renew_mode")        
        self.date_format = valid_config.get("date_format")
        self.table_name = valid_config.get("table_name")
        self.date_field = valid_config.get("date_field")
        self.default_date_range = valid_config.get("default_date_range")
        self.apis = valid_config.get("apis")
        self.params = valid_config.get("params")
        self.field_mapping = valid_config.get("field_mapping")
        self.requires_date_range = valid_config.get("requires_date_range")
        pass