from __future__ import annotations

import threading
from pathlib import Path

from data_pipeline.io_utils import read_json, write_json
from schemas import ChatMessage, SessionState


class JSONMemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()

    def get_session(self, session_id: str) -> SessionState:
        with self.lock:
            payload = read_json(self.path, default={})
            if session_id not in payload:
                return SessionState(session_id=session_id)
            return SessionState.model_validate(payload[session_id])

    def save_session(self, session: SessionState) -> None:
        with self.lock:
            payload = read_json(self.path, default={})
            payload[session.session_id] = session.model_dump()
            write_json(self.path, payload)

    def append_message(self, session_id: str, role: str, content: str) -> SessionState:
        session = self.get_session(session_id)
        session.history.append(ChatMessage(role=role, content=content))
        self.save_session(session)
        return session

    def reset_session(self, session_id: str) -> None:
        with self.lock:
            payload = read_json(self.path, default={})
            payload.pop(session_id, None)
            write_json(self.path, payload)
