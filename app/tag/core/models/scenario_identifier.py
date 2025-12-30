"""
Scenario Identifier - Scenario 标识符

封装 scenario name 和 version，方便使用和传递。
"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioIdentifier:
    """
    Scenario 标识符
    
    封装 scenario name 和 version，提供类型安全和便捷使用。
    
    特性：
    - 不可变（frozen=True），可以作为字典的 key
    - 实现了 __eq__ 和 __hash__，支持集合操作
    - 实现了 __str__ 和 __repr__，方便调试和日志
    
    使用示例：
        # 创建标识符
        scenario_id = ScenarioIdentifier(name="market_value_bucket", version="1.0")
        
        # 从 settings 创建
        scenario_id = ScenarioIdentifier.from_settings(settings)
        
        # 从字典创建
        scenario_id = ScenarioIdentifier.from_dict({"name": "market_value_bucket", "version": "1.0"})
        
        # 作为字典的 key
        cache = {scenario_id: calculator_instance}
        
        # 字符串表示
        print(scenario_id)  # "market_value_bucket@1.0"
    """
    name: str
    version: str
    
    def __str__(self) -> str:
        """
        字符串表示：name@version
        
        Returns:
            str: "name@version" 格式的字符串
        """
        return f"{self.name}@{self.version}"
    
    def __repr__(self) -> str:
        """
        对象表示
        
        Returns:
            str: ScenarioIdentifier(name="...", version="...")
        """
        return f"ScenarioIdentifier(name={self.name!r}, version={self.version!r})"
    
    def to_dict(self) -> Dict[str, str]:
        """
        转换为字典
        
        Returns:
            Dict[str, str]: {"name": ..., "version": ...}
        """
        return {
            "name": self.name,
            "version": self.version
        }
    
    @classmethod
    def from_settings(cls, settings: Dict[str, Any]) -> 'ScenarioIdentifier':
        """
        从 settings 字典创建 ScenarioIdentifier
        
        Args:
            settings: Settings 字典，必须包含 scenario.name 和 scenario.version
            
        Returns:
            ScenarioIdentifier: Scenario 标识符
            
        Raises:
            ValueError: 如果 settings 格式不正确
        """
        if "scenario" not in settings:
            raise ValueError("Settings 缺少 'scenario' 字段")
        
        scenario = settings["scenario"]
        if not isinstance(scenario, dict):
            raise ValueError("Settings.scenario 必须是字典类型")
        
        if "name" not in scenario:
            raise ValueError("Settings.scenario 缺少 'name' 字段")
        if "version" not in scenario:
            raise ValueError("Settings.scenario 缺少 'version' 字段")
        
        return cls(
            name=scenario["name"],
            version=scenario["version"]
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ScenarioIdentifier':
        """
        从字典创建 ScenarioIdentifier
        
        Args:
            data: 字典，必须包含 "name" 和 "version" 键
            
        Returns:
            ScenarioIdentifier: Scenario 标识符
            
        Raises:
            ValueError: 如果字典格式不正确
        """
        if "name" not in data:
            raise ValueError("字典缺少 'name' 字段")
        if "version" not in data:
            raise ValueError("字典缺少 'version' 字段")
        
        return cls(
            name=data["name"],
            version=data["version"]
        )
    
    @classmethod
    def from_scenario_record(cls, scenario_record: Dict[str, Any]) -> 'ScenarioIdentifier':
        """
        从数据库 scenario 记录创建 ScenarioIdentifier
        
        Args:
            scenario_record: 数据库 scenario 记录，必须包含 "name" 和 "version" 字段
            
        Returns:
            ScenarioIdentifier: Scenario 标识符
            
        Raises:
            ValueError: 如果记录格式不正确
        """
        if "name" not in scenario_record:
            raise ValueError("Scenario 记录缺少 'name' 字段")
        if "version" not in scenario_record:
            raise ValueError("Scenario 记录缺少 'version' 字段")
        
        return cls(
            name=scenario_record["name"],
            version=scenario_record["version"]
        )
