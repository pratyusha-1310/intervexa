"""
session_registry.py (service)
-----------------------------
In-memory registry for active InterviewSession instances.

Responsibility
~~~~~~~~~~~~~~
Maintains the mapping of `session_id -> InterviewSession` in memory.
Serves as the single source of truth for retrieving and managing live interview state.

This module does NOT:
- execute HTTP routes
- call any LLM
- generate feedback

Public API
~~~~~~~~~~
- ``SessionRegistry`` (Class)
- ``SessionRegistryError`` (Base exception)
- ``SessionNotFoundError`` (Exception)
- ``DuplicateSessionError`` (Exception)
- ``get_session_registry()`` (Singleton accessor)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

from app.services.interview_session import InterviewSession


# ── Exceptions ─────────────────────────────────────────────────────────────────

class SessionRegistryError(Exception):
    """Base exception for all Session Registry errors."""


class SessionNotFoundError(SessionRegistryError, KeyError):
    """Raised when looking up a session_id that does not exist in the registry."""


class DuplicateSessionError(SessionRegistryError, ValueError):
    """Raised when attempting to register a session_id that already exists."""


# ── Session Registry ───────────────────────────────────────────────────────────

class SessionRegistry:
    """
    In-memory storage and manager for active InterviewSession objects.

    Provides O(1) retrieval, lifecycle tracking, and clean error handling.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, InterviewSession] = {}

    def create_session(self, session: InterviewSession) -> str:
        """
        Registers a new InterviewSession in memory.

        Args:
            session: The InterviewSession instance to register.

        Returns:
            The session_id string.

        Raises:
            DuplicateSessionError: If session.session_id already exists in registry.
        """
        session_id = session.session_id
        if session_id in self._sessions:
            raise DuplicateSessionError(
                f"Session with ID '{session_id}' already exists in registry."
            )
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> InterviewSession:
        """
        Retrieves an active InterviewSession by its session_id in O(1) time.

        Args:
            session_id: The unique session identifier string.

        Returns:
            The matching InterviewSession instance.

        Raises:
            SessionNotFoundError: If no session with session_id exists.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(
                f"No active session found with ID '{session_id}'."
            )
        return self._sessions[session_id]

    def session_exists(self, session_id: str) -> bool:
        """
        Checks if a session_id exists in the registry.

        Args:
            session_id: The session identifier to check.

        Returns:
            True if the session exists, False otherwise.
        """
        return session_id in self._sessions

    def remove_session(self, session_id: str) -> None:
        """
        Removes an active session from the registry.

        Args:
            session_id: The session identifier to remove.

        Raises:
            SessionNotFoundError: If the session_id does not exist.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(
                f"Cannot remove: session with ID '{session_id}' not found."
            )
        del self._sessions[session_id]

    def clear(self) -> None:
        """Removes all active sessions from the registry."""
        self._sessions.clear()

    def active_session_count(self) -> int:
        """Returns the total number of currently active sessions in memory."""
        return len(self._sessions)

    def list_active_sessions(self) -> List[str]:
        """Returns a list of all active session_id strings."""
        return list(self._sessions.keys())


# ── Global Singleton ───────────────────────────────────────────────────────────

@lru_cache
def get_session_registry() -> SessionRegistry:
    """Returns a process-wide singleton instance of SessionRegistry."""
    return SessionRegistry()
