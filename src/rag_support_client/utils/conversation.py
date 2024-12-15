"""
Conversation management module for RAG support application.

This module provides thread-safe conversation handling with memory retention
and automatic cleanup capabilities. It manages multiple user sessions
and maintains conversation history in a format compatible with LangChain.
Includes automatic periodic cleanup of expired sessions and strong session isolation.

Example:
    manager = ConversationManager(max_history=20)
    session_id = manager.create_session_id()
    manager.add_message(session_id, "human", "Hello")
    history = manager.get_history(session_id)

Returns:
    Module containing ConversationManager and Message classes
"""

import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from threading import Lock, Thread


@dataclass
class Message:
    """Represents a single message in a conversation"""

    role: str  # "human" or "assistant"
    content: str
    timestamp: datetime = datetime.now()

    def to_dict(self) -> dict:
        """Converts message to dict format for LangChain memory"""
        role_mapping = {"human": "user", "assistant": "assistant", "system": "system"}
        return {"role": role_mapping.get(self.role, self.role), "content": self.content}


class ConversationManager:
    """Thread-safe conversation manager with memory retention and automated cleanup"""

    def __init__(
        self,
        max_history: int = 20,
        session_timeout: int = 3600,
        cleanup_interval: int = 300,
    ) -> None:
        self._conversations: dict[str, list[Message]] = {}
        self._last_activity: dict[str, datetime] = {}
        self._session_locks: dict[str, Lock] = {}
        self.max_history = max_history
        self.session_timeout = session_timeout  # seconds
        self._master_lock = Lock()
        self._cleanup_interval = cleanup_interval
        self._cleanup_thread: Thread | None = None
        self._running = True
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """Starts background thread for periodic session cleanup"""

        def cleanup_loop() -> None:
            while self._running:
                self._cleanup_expired_sessions()
                time.sleep(self._cleanup_interval)
            return None

        self._cleanup_thread = Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def stop(self) -> None:
        """Stops the cleanup thread and cleans up resources"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1.0)
        with self._master_lock:
            self._conversations.clear()
            self._last_activity.clear()
            self._session_locks.clear()

    def _get_session_lock(self, session_id: str) -> Lock:
        """Gets or creates a lock for a specific session"""
        with self._master_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = Lock()
            return self._session_locks[session_id]

    def _cleanup_expired_sessions(self) -> None:
        """Removes expired sessions based on timeout"""
        current_time = datetime.now()
        with self._master_lock:
            expired_sessions = [
                session_id
                for session_id, last_activity in self._last_activity.items()
                if (current_time - last_activity).total_seconds() > self.session_timeout
            ]

            for session_id in expired_sessions:
                session_lock = self._session_locks.get(session_id)
                if session_lock:
                    with session_lock:
                        self._conversations.pop(session_id, None)
                        self._last_activity.pop(session_id, None)
                        self._session_locks.pop(session_id, None)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Adds message to conversation with automatic history trimming"""
        session_lock = self._get_session_lock(session_id)
        with session_lock:
            if session_id not in self._conversations:
                self._conversations[session_id] = []

            message = Message(role=role, content=content)
            self._conversations[session_id].append(message)
            self._last_activity[session_id] = datetime.now()

            if len(self._conversations[session_id]) > self.max_history:
                self._conversations[session_id] = self._conversations[session_id][
                    -self.max_history :
                ]

    def get_history(self, session_id: str) -> list[dict]:
        """Returns conversation history in LangChain-compatible format"""
        session_lock = self._get_session_lock(session_id)
        with session_lock:
            messages = self._conversations.get(session_id, [])
            return [msg.to_dict() for msg in messages]

    def clear_conversation(self, session_id: str) -> None:
        """Removes conversation history for given session"""
        session_lock = self._get_session_lock(session_id)
        with session_lock:
            self._conversations.pop(session_id, None)
            self._last_activity.pop(session_id, None)
            self._session_locks.pop(session_id, None)

    def get_active_sessions(self) -> list[str]:
        """Returns list of active session IDs"""
        with self._master_lock:
            self._cleanup_expired_sessions()
            return list(self._conversations.keys())

    def get_session_time_remaining(self, session_id: str) -> int | None:
        """Returns remaining time in seconds for session or None if expired"""
        with self._master_lock:
            if session_id not in self._last_activity:
                return None

            elapsed = (datetime.now() - self._last_activity[session_id]).total_seconds()
            remaining = self.session_timeout - elapsed
            return max(0, int(remaining))

    @staticmethod
    def create_session_id() -> str:
        """Generates unique session ID"""
        return str(uuid.uuid4())
