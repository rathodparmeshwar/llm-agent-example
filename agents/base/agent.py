"""Base agent interface for all specialized agents."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any
from uuid import UUID

class BaseAgent(ABC):
    """Base class for all agents.
    
    All specialized agents must inherit from this class and implement
    its abstract methods. This ensures consistent behavior across
    different agent types.
    """
    
    @property
    @abstractmethod
    def route_code(self) -> str:
        """The route code this agent handles.
        
        Returns:
            str: The unique route code for this agent type.
        """
        pass
        
    @abstractmethod
    async def process_message(
        self,
        message: str,
        conversation_id: UUID,
        context: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Process a message and yield response chunks.
        
        Args:
            message (str): The user's message to process
            conversation_id (UUID): The ID of the current conversation
            context (Dict[str, Any]): The conversation context including any
                collected data and state information

        Yields:
            str: Response chunks that can be streamed to the client
        """
        pass 