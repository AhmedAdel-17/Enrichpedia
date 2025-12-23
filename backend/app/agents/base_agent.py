from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        logging.basicConfig(level=logging.INFO)

    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        pass

    def log_info(self, message: str) -> None:
        self.logger.info(f"[{self.name}] {message}")

    def log_error(self, message: str) -> None:
        self.logger.error(f"[{self.name}] {message}")

    def log_warning(self, message: str) -> None:
        self.logger.warning(f"[{self.name}] {message}")

    def validate_input(self, input_data: Any, required_fields: list) -> bool:
        if isinstance(input_data, dict):
            for field in required_fields:
                if field not in input_data:
                    self.log_error(f"Missing required field: {field}")
                    return False
        return True
