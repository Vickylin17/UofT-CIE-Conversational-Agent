from __future__ import annotations

from datetime import datetime, timezone
import threading
from pathlib import Path

from data_pipeline.io_utils import read_json, write_json
from schemas import ChatMessage, SessionState


class JSONMemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _derive_title(self, session: SessionState) -> str:
        if session.title and session.title.strip():
            return session.title.strip()
        for message in session.history:
            if message.role == "user" and message.content.strip():
                return message.content.strip()[:48]
        return "New chat"

    def get_session(self, session_id: str) -> SessionState:
        with self.lock:
            payload = read_json(self.path, default={})
            if session_id not in payload:
                now = self._now_iso()
                return SessionState(session_id=session_id, title="New chat", created_at=now, updated_at=now)
            session = SessionState.model_validate(payload[session_id])
            if not session.created_at:
                session.created_at = self._now_iso()
            if not session.updated_at:
                session.updated_at = session.created_at
            if not session.title:
                session.title = self._derive_title(session)
            return session

    def save_session(self, session: SessionState) -> None:
        with self.lock:
            payload = read_json(self.path, default={})
            now = self._now_iso()
            if not session.created_at:
                session.created_at = now
            session.updated_at = now
            if not session.title:
                session.title = self._derive_title(session)
            payload[session.session_id] = session.model_dump()
            write_json(self.path, payload)

    def append_message(self, session_id: str, role: str, content: str) -> SessionState:
        session = self.get_session(session_id)
        session.history.append(ChatMessage(role=role, content=content))
        self.save_session(session)
        return session

    def rename_session(self, session_id: str, title: str) -> None:
        with self.lock:
            payload = read_json(self.path, default={})
            raw = payload.get(session_id)
            if raw is None:
                return
            session = SessionState.model_validate(raw)
            cleaned_title = " ".join(title.split()).strip()
            session.title = cleaned_title[:80] if cleaned_title else self._derive_title(session)
            session.updated_at = self._now_iso()
            payload[session_id] = session.model_dump()
            write_json(self.path, payload)

    def list_sessions(self, include_archived: bool = False) -> list[dict[str, str | int | bool]]:
        with self.lock:
            payload = read_json(self.path, default={})
            sessions: list[dict[str, str | int | bool]] = []
            for raw in payload.values():
                session = SessionState.model_validate(raw)
                if session.archived and not include_archived:
                    continue
                title = self._derive_title(session)
                preview = ""
                for message in reversed(session.history):
                    if message.content.strip():
                        preview = message.content.strip()
                        break
                sessions.append(
                    {
                        "session_id": session.session_id,
                        "title": title,
                        "preview": preview[:80],
                        "updated_at": session.updated_at or "",
                        "history_len": len(session.history),
                        "archived": session.archived,
                    }
                )

            sessions.sort(key=lambda item: str(item["updated_at"]), reverse=True)
            return sessions

    def archive_session(self, session_id: str) -> None:
        with self.lock:
            payload = read_json(self.path, default={})
            raw = payload.get(session_id)
            if raw is None:
                return
            session = SessionState.model_validate(raw)
            session.archived = True
            session.updated_at = self._now_iso()
            payload[session_id] = session.model_dump()
            write_json(self.path, payload)

    def unarchive_session(self, session_id: str) -> None:
        with self.lock:
            payload = read_json(self.path, default={})
            raw = payload.get(session_id)
            if raw is None:
                return
            session = SessionState.model_validate(raw)
            session.archived = False
            session.updated_at = self._now_iso()
            payload[session_id] = session.model_dump()
            write_json(self.path, payload)

    def delete_session(self, session_id: str) -> None:
        self.reset_session(session_id)

    def reset_session(self, session_id: str) -> None:
        with self.lock:
            payload = read_json(self.path, default={})
            payload.pop(session_id, None)
            write_json(self.path, payload)
