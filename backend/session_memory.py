"""
Persistent Session Memory Store for AURA 3D Learning Lab.

Maintains stateful continuous session context:
- Active ModelSpec and revision history (undo/redo)
- Current selected component & focus
- Full conversation message turns
- Uploaded study material context & identified topics
- Active Quiz progress & scores
- User settings (TTS, difficulty, theme)
"""

from __future__ import annotations

import time
from typing import Any, Optional


class SessionState:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.created_at: float = time.time()
        self.last_active: float = time.time()
        
        # 3D Model State
        self.current_model: Optional[dict[str, Any]] = None
        self.model_history: list[dict[str, Any]] = []
        self.selected_component_id: Optional[str] = None
        
        # Educational & Conversation Context
        self.topic: str = "Step-Down Electrical Transformer"
        self.document_context: str = ""
        self.document_topics: list[dict[str, Any]] = []
        self.messages: list[dict[str, str]] = []
        
        # Teacher & Quiz State
        self.current_lesson: Optional[dict[str, Any]] = None
        self.current_quiz: Optional[dict[str, Any]] = None
        self.quiz_scores: list[dict[str, Any]] = []
        
        # Preferences
        self.tts_enabled: bool = True
        self.difficulty: str = "Intermediate"

    def set_model(self, model_spec: dict[str, Any], record_history: bool = True):
        if record_history and self.current_model:
            self.model_history.append(dict(self.current_model))
            # Limit history depth
            if len(self.model_history) > 15:
                self.model_history.pop(0)
        self.current_model = dict(model_spec)
        self.topic = model_spec.get("topic") or self.topic
        self.last_active = time.time()

    def undo_model(self) -> Optional[dict[str, Any]]:
        """Revert to previous ModelSpec revision if available."""
        if self.model_history:
            prev = self.model_history.pop()
            self.current_model = prev
            self.topic = prev.get("topic") or self.topic
            self.last_active = time.time()
            return self.current_model
        return None

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > 40:
            self.messages.pop(0)
        self.last_active = time.time()

    def update_state(self, updates: dict[str, Any]):
        if "selected_component_id" in updates:
            self.selected_component_id = updates["selected_component_id"]
        if "tts_enabled" in updates:
            self.tts_enabled = bool(updates["tts_enabled"])
        if "difficulty" in updates:
            self.difficulty = str(updates["difficulty"])
        if "document_context" in updates:
            self.document_context = str(updates["document_context"])
        self.last_active = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "topic": self.topic,
            "has_model": self.current_model is not None,
            "selected_component_id": self.selected_component_id,
            "model_history_length": len(self.model_history),
            "message_count": len(self.messages),
            "has_document": bool(self.document_context),
            "tts_enabled": self.tts_enabled,
            "difficulty": self.difficulty,
            "current_model": self.current_model,
            "current_lesson": self.current_lesson,
            "current_quiz": self.current_quiz,
        }


class SessionMemoryManager:
    """Manages active user sessions in memory."""

    def __init__(self):
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str | None = None) -> SessionState:
        sid = session_id or "default_user_session"
        if sid not in self._sessions:
            self._sessions[sid] = SessionState(sid)
        session = self._sessions[sid]
        session.last_active = time.time()
        return session

    def reset(self, session_id: str | None = None) -> SessionState:
        sid = session_id or "default_user_session"
        self._sessions[sid] = SessionState(sid)
        return self._sessions[sid]

    @classmethod
    def get_session(cls, session_id: str | None = None) -> SessionState:
        return session_manager.get_or_create(session_id)

    @classmethod
    def reset_session(cls, session_id: str | None = None) -> SessionState:
        return session_manager.reset(session_id)





# Global session manager instance
session_manager = SessionMemoryManager()
