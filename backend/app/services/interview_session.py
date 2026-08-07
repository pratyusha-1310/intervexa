"""
interview_session.py (service)
------------------------------
Manages the lifecycle of a single interview session.

Responsibility
~~~~~~~~~~~~~~
This component owns interview **state** only:
- tracking which curriculum day we're on
- counting questions asked
- recording completed days
- detecting when the interview is finished
- maintaining a lightweight conversation history

It does NOT:
- generate interview questions
- call any LLM
- evaluate candidate answers
- produce feedback
- expose HTTP endpoints

Public API
~~~~~~~~~~
- ``InterviewSession(plan)``  — constructor
- ``start_session()``         — begin the interview
- ``get_current_day()``       — return the active SelectedDay
- ``get_current_question_number()`` — 1-based next question number
- ``advance_question()``      — record that a question was asked
- ``complete_day()``          — finalise current day, advance to next
- ``mark_interview_complete()`` — end the interview
- ``is_complete()``           — check if the interview has finished
- ``add_conversation_entry()`` — append a message to the history
- ``get_conversation_history()`` — retrieve the full history
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.schemas.interview_session import (
    ConversationEntry,
    InterviewSessionState,
)


# ── Custom Exceptions ─────────────────────────────────────────────────────────


class SessionNotStartedError(RuntimeError):
    """Raised when an operation requires the session to have been started."""


class SessionAlreadyStartedError(RuntimeError):
    """Raised when ``start_session()`` is called on an already-running session."""


class SessionAlreadyCompleteError(RuntimeError):
    """Raised when an operation is attempted on a completed interview."""


class DayBudgetExhaustedError(RuntimeError):
    """Raised when all planned questions for the current day have been asked."""


class QuestionBudgetExhaustedError(RuntimeError):
    """Raised when the total planned question budget has been reached."""


class NoDaysRemainingError(RuntimeError):
    """Raised when ``complete_day()`` is called but no more days are available."""


# ── InterviewSession ──────────────────────────────────────────────────────────


class InterviewSession:
    """Stateful controller for a single interview session.

    Wraps an :class:`~app.schemas.interview_session.InterviewSessionState`
    and exposes a clean behavioural API for the Interview Engine to drive
    the interview forward step-by-step.

    Args:
        plan: A fully-populated :class:`~app.schemas.interview_plan.InterviewPlan`
              as produced by ``build_interview_plan()``.
    """

    def __init__(self, plan: InterviewPlan, session_id: Optional[str] = None) -> None:
        actual_session_id = session_id or str(uuid4())

        # Stamp the session_id onto the plan for traceability.
        plan = plan.model_copy(update={"session_id": actual_session_id})

        self._state = InterviewSessionState(
            session_id=actual_session_id,
            candidate_id=plan.candidate_id,
            plan=plan,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state(self) -> InterviewSessionState:
        """Return the full, serialisable session state."""
        return self._state

    @property
    def session_id(self) -> str:
        return self._state.session_id

    @property
    def candidate_id(self) -> str:
        return self._state.candidate_id

    @property
    def plan(self) -> InterviewPlan:
        return self._state.plan

    @property
    def total_questions_asked(self) -> int:
        return self._state.total_questions_asked

    @property
    def completed_days(self) -> list[int]:
        """Return a copy of the completed-day list."""
        return list(self._state.completed_days)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_session(self) -> None:
        """Mark the interview as started.

        Raises:
            SessionAlreadyStartedError: If the session was already started.
        """
        if self._state.interview_started:
            raise SessionAlreadyStartedError(
                f"Session '{self.session_id}' has already been started."
            )
        self._state.interview_started = True
        self._state.started_at = datetime.now(timezone.utc)

    def mark_interview_complete(self) -> None:
        """Explicitly end the interview.

        Raises:
            SessionNotStartedError: If the session was never started.
            SessionAlreadyCompleteError: If the interview was already completed.
        """
        self._require_started()
        if self._state.interview_completed:
            raise SessionAlreadyCompleteError(
                f"Session '{self.session_id}' is already complete."
            )
        self._state.interview_completed = True
        self._state.completed_at = datetime.now(timezone.utc)

    def is_complete(self) -> bool:
        """Return ``True`` if the interview has been marked as complete."""
        return self._state.interview_completed

    # ── Navigation ────────────────────────────────────────────────────────────

    def get_current_day(self) -> SelectedDay:
        """Return the :class:`SelectedDay` currently being interviewed.

        Raises:
            SessionNotStartedError: If the session was never started.
            SessionAlreadyCompleteError: If the interview is complete.
        """
        self._require_active()
        return self._state.plan.selected_days[self._state.current_day_index]

    def get_current_question_number(self) -> int:
        """Return the 1-based sequence number of the **next** question to ask.

        Example: if 0 questions have been asked, returns 1.
        After ``advance_question()`` is called once, returns 2.

        This value counts across the entire interview, not per-day.

        Raises:
            SessionNotStartedError: If the session was never started.
            SessionAlreadyCompleteError: If the interview is complete.
        """
        self._require_active()
        return self._state.total_questions_asked + 1

    # ── Question Tracking ─────────────────────────────────────────────────────

    def advance_question(self) -> int:
        """Record that a question was asked and increment counters.

        Returns:
            The new ``total_questions_asked`` count after incrementing.

        Raises:
            SessionNotStartedError:       Session not started.
            SessionAlreadyCompleteError:  Interview already finished.
            DayBudgetExhaustedError:      All planned questions for the current
                                          day have been asked — call
                                          ``complete_day()`` first.
            QuestionBudgetExhaustedError: The overall question budget is
                                          exhausted.
        """
        self._require_active()

        current_day = self.get_current_day()

        if self._state.current_question_in_day >= current_day.planned_questions:
            raise DayBudgetExhaustedError(
                f"All {current_day.planned_questions} planned question(s) for "
                f"day {current_day.day} ('{current_day.title}') have been "
                f"asked. Call complete_day() to advance."
            )

        if self._state.total_questions_asked >= self._state.plan.planned_question_count:
            raise QuestionBudgetExhaustedError(
                f"Total question budget of "
                f"{self._state.plan.planned_question_count} has been reached."
            )

        self._state.current_question_in_day += 1
        self._state.total_questions_asked += 1
        return self._state.total_questions_asked

    # ── Day Progression ───────────────────────────────────────────────────────

    def complete_day(self) -> SelectedDay | None:
        """Finalise the current curriculum day and advance to the next.

        The current day is added to ``completed_days``. If more days remain,
        the session advances and the per-day question counter resets. If no
        more days remain, the interview is automatically marked complete.

        Returns:
            The next :class:`SelectedDay` if one exists, or ``None`` if the
            interview has just been completed.

        Raises:
            SessionNotStartedError:       Session not started.
            SessionAlreadyCompleteError:  Interview already finished.
        """
        self._require_active()

        finished_day = self._state.plan.selected_days[self._state.current_day_index]
        self._state.completed_days.append(finished_day.day)

        next_index = self._state.current_day_index + 1

        if next_index >= len(self._state.plan.selected_days):
            # No more days — interview is done.
            self._state.interview_completed = True
            self._state.completed_at = datetime.now(timezone.utc)
            return None

        # Advance to the next day.
        self._state.current_day_index = next_index
        self._state.current_question_in_day = 0
        return self._state.plan.selected_days[next_index]

    # ── Conversation History ──────────────────────────────────────────────────

    def add_conversation_entry(
        self,
        role: str,
        content: str,
    ) -> ConversationEntry:
        """Append a message to the conversation history.

        Args:
            role:    ``"interviewer"`` or ``"candidate"``.
            content: The message text.

        Returns:
            The newly created :class:`ConversationEntry`.

        Raises:
            SessionNotStartedError: Session not started.
        """
        self._require_started()

        current_day = self._state.plan.selected_days[self._state.current_day_index]
        turn_number = len(self._state.conversation_history) + 1

        entry = ConversationEntry(
            turn_number=turn_number,
            curriculum_day=current_day.day,
            role=role,
            content=content,
        )
        self._state.conversation_history.append(entry)
        return entry

    def get_conversation_history(self) -> list[ConversationEntry]:
        """Return a copy of the full conversation history."""
        return list(self._state.conversation_history)

    # ── Guards ────────────────────────────────────────────────────────────────

    def _require_started(self) -> None:
        """Raise if the session has not been started."""
        if not self._state.interview_started:
            raise SessionNotStartedError(
                f"Session '{self.session_id}' has not been started yet. "
                "Call start_session() first."
            )

    def _require_active(self) -> None:
        """Raise if the session is not in an active (started + not complete) state."""
        self._require_started()
        if self._state.interview_completed:
            raise SessionAlreadyCompleteError(
                f"Session '{self.session_id}' is already complete."
            )
