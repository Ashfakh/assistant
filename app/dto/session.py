from dataclasses import dataclass, field

from app.dto.chat import ChatMessage


@dataclass
class SessionDTO:
    id: str
    chat_history: list[ChatMessage] = field(default_factory=list)

@dataclass
class QueryDTO:
    message: str
    session_dto: SessionDTO
