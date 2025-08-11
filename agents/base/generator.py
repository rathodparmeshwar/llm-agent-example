"""Base class for generator agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from anthropic import AsyncAnthropic

class BaseGeneratorAgent(ABC):
    """Base class for agents that generate synthetic data."""
    
    def __init__(self, client: AsyncAnthropic):
        """Initialize the generator agent.
        
        Args:
            client: The Anthropic client
        """
        self.client = client

    @property
    @abstractmethod
    def route_code(self) -> str:
        """Get the route code for this agent."""
        pass

    @abstractmethod
    async def generate(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate synthetic data based on provided parameters.
        
        Args:
            params: Generation parameters
            context: Optional context information
            
        Returns:
            Generated data with success/error information
        """
        pass 