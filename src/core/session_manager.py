"""
Session manager — holds in-memory state per session (player party + trainer + strategy).
Each session is keyed by a UUID. For production, swap the dict with Redis or a DB.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Session:
    session_id: str
    player_data: Optional[dict] = None       # from extracter
    trainer_data: Optional[dict] = None      # from researcher
    strategy_data: Optional[dict] = None     # from calculator
    display_data: Optional[dict] = None      # from displayer
    trainer_hint: Optional[str | int] = None # name or index of next trainer

    @property
    def is_ready_for_calc(self) -> bool:
        return self.player_data is not None and self.trainer_data is not None

    @property
    def is_complete(self) -> bool:
        return self.display_data is not None


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        sid = str(uuid.uuid4())
        session = Session(session_id=sid)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def update(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_ids(self) -> list[str]:
        return list(self._sessions.keys())


session_manager = SessionManager()
