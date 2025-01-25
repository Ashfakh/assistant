from dataclasses import dataclass
from typing import List, Optional


@dataclass
class HealthMemory:
    current_activity: str = None
    exercise_script: Optional[List[str]] = None
    script_index: int = 0
    alert: Optional[bool] = False
