from dataclasses import dataclass


@dataclass
class AssistantMemory:
    current_state: str = "GenericQuery"
