from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Optional
import asyncio
import uuid


T = TypeVar("T")


class Actor(Generic[T], ABC):
    def __init__(self, initial_memory: Optional[T], actor_id: Optional[str] = None):
        """
        Initialize actor with either new or persisted memory.
        If no actor_id is provided, generates a new UUID.

        Args:
            initial_memory: Default memory if no persisted state exists
            actor_id: Optional identifier to retrieve persisted memory
        """
        self._id: str = actor_id or str(uuid.uuid4())
        self._memory: T = initial_memory or T()

    @property
    def id(self) -> str:
        """
        Get the actor's identifier.

        Returns:
            str: The actor's unique identifier
        """
        return self._id

    @property
    def memory(self) -> T:
        return self._memory

    def _load_memory(self, actor_id: str) -> T:
        """
        Load persisted memory for this actor.
        Must be implemented by concrete actors.

        Args:
            actor_id: The identifier for the persisted memory
        Returns:
            T: The loaded memory object
        """
        pass

    @abstractmethod
    async def on_receive(self, message: Any):
        """
        Handle incoming messages and orchestrate tasks.
        Must be implemented by concrete actors.

        Args:
            message: The message to be processed
        Returns:
            Any: The result of processing the message
        """
        pass

    async def ask(self, message: Any):
        """
        Blocking call to get a result from the actor.

        Args:
            message: The message to be processed
        Returns:
            Any: The result from on_receive
        """
        return await self.on_receive(message)

    def tell(self, message: Any):
        """
        Non-blocking call to send a message to the actor.

        Args:
            message: The message to be processed
        """
        asyncio.create_task(self.on_receive(message))

    def get_memory(self) -> T:
        """
        Accessor for the actor's local memory.

        Returns:
            T: The actor's memory
        """
        return self._memory

    def set_memory(self, memory: T):
        """
        Mutator for the actor's local memory.

        Args:
            memory: The new memory object
        """
        self._memory = memory

    def persist_memory(self, external_storage: Any):
        """
        Store the actor's memory externally.
        Must be implemented by persistant actors.

        Args:
            external_storage: The storage mechanism to persist memory
        """
        pass
