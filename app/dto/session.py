from dataclasses import dataclass, field
from enum import Enum

from app.dto.chat import ChatMessage

class UserType(Enum):
    DAD = "dad"
    SON = "son"

@dataclass
class SessionDTO:
    id: str
    active_user: UserType
    language: str
    chat_history: list[ChatMessage] = field(default_factory=list)

@dataclass
class QueryDTO:
    message: str
    session_dto: SessionDTO
