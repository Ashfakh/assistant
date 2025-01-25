from dataclasses import dataclass


@dataclass
class MessageMemory:
    current_state: str = "GenericQuery"
