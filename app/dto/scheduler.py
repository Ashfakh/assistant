from dataclasses import dataclass


@dataclass
class SchedulerMemory:
    current_state: str = "GenericQuery"
