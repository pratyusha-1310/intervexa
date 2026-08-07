"""
tests/test_interview_session.py
-------------------------------
Unit tests for ``app.services.interview_session.InterviewSession``.

All tests use a synthetic InterviewPlan fixture so they are fully
deterministic and independent of the real JSON data on disk.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.schemas.interview_session import ConversationEntry, InterviewSessionState
from app.services.interview_session import (
    DayBudgetExhaustedError,
    InterviewSession,
    NoDaysRemainingError,
    QuestionBudgetExhaustedError,
    SessionAlreadyCompleteError,
    SessionAlreadyStartedError,
    SessionNotStartedError,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════


def _make_selected_day(
    day: int,
    planned_questions: int = 2,
    module_number: int = 1,
    module_title: str = "Module Alpha",
    priority: int = 2,
) -> SelectedDay:
    """Factory for a minimal SelectedDay."""
    return SelectedDay(
        day=day,
        title=f"Day {day} Topic",
        module_number=module_number,
        module_title=module_title,
        type="BUILD",
        tools=[f"ToolX-{day}"],
        objectives=[f"Objective for day {day}"],
        selection_reason="Test reason",
        priority=priority,
        planned_questions=planned_questions,
    )


def _make_plan(
    days_config: list[tuple[int, int]] | None = None,
) -> InterviewPlan:
    """Factory for a minimal InterviewPlan.

    Args:
        days_config: List of ``(day_number, planned_questions)`` tuples.
                     Defaults to four days with 2 questions each (total 8).
    """
    if days_config is None:
        days_config = [(10, 2), (15, 2), (20, 2), (25, 2)]

    selected_days = [
        _make_selected_day(day=d, planned_questions=q)
        for d, q in days_config
    ]
    questions_per_day = {d: q for d, q in days_config}

    return InterviewPlan(
        candidate_id="TEST-001",
        candidate_name="Test User",
        selected_days=selected_days,
        selected_modules=["Module Alpha"],
        planned_question_count=sum(q for _, q in days_config),
        questions_per_day=questions_per_day,
        initial_difficulty="Medium",
        evaluation_goals=["Technical Understanding", "Problem Solving"],
        interview_strategy="Cover selected curriculum topics in priority order.",
        selection_reasons={d: "Test reason" for d, _ in days_config},
    )


@pytest.fixture()
def plan() -> InterviewPlan:
    """Default plan: 4 days × 2 questions = 8 total."""
    return _make_plan()


@pytest.fixture()
def session(plan: InterviewPlan) -> InterviewSession:
    """A fresh, un-started session."""
    return InterviewSession(plan)


@pytest.fixture()
def started_session(session: InterviewSession) -> InterviewSession:
    """A session that has been started."""
    session.start_session()
    return session


# ══════════════════════════════════════════════════════════════════════════════
# Initialisation
# ══════════════════════════════════════════════════════════════════════════════


class TestSessionInitialisation:
    def test_session_id_is_generated(self, session: InterviewSession) -> None:
        assert session.session_id is not None
        assert len(session.session_id) > 0

    def test_candidate_id_from_plan(self, session: InterviewSession) -> None:
        assert session.candidate_id == "TEST-001"

    def test_plan_session_id_stamped(self, session: InterviewSession) -> None:
        """The plan's session_id should be stamped with the session's id."""
        assert session.plan.session_id == session.session_id

    def test_initial_state_not_started(self, session: InterviewSession) -> None:
        assert session.state.interview_started is False
        assert session.state.interview_completed is False

    def test_initial_counters_at_zero(self, session: InterviewSession) -> None:
        assert session.state.current_day_index == 0
        assert session.state.current_question_in_day == 0
        assert session.state.total_questions_asked == 0

    def test_completed_days_empty(self, session: InterviewSession) -> None:
        assert session.completed_days == []

    def test_conversation_history_empty(self, session: InterviewSession) -> None:
        assert session.get_conversation_history() == []

    def test_state_is_serialisable(self, session: InterviewSession) -> None:
        """The state model must be JSON-serialisable for persistence."""
        data = session.state.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["session_id"] == session.session_id


# ══════════════════════════════════════════════════════════════════════════════
# Lifecycle – start / complete
# ══════════════════════════════════════════════════════════════════════════════


class TestSessionLifecycle:
    def test_start_session_sets_flags(self, session: InterviewSession) -> None:
        session.start_session()
        assert session.state.interview_started is True
        assert session.state.started_at is not None

    def test_start_session_twice_raises(
        self, started_session: InterviewSession
    ) -> None:
        with pytest.raises(SessionAlreadyStartedError):
            started_session.start_session()

    def test_mark_complete_sets_flags(
        self, started_session: InterviewSession
    ) -> None:
        started_session.mark_interview_complete()
        assert started_session.is_complete() is True
        assert started_session.state.completed_at is not None

    def test_mark_complete_before_start_raises(
        self, session: InterviewSession
    ) -> None:
        with pytest.raises(SessionNotStartedError):
            session.mark_interview_complete()

    def test_mark_complete_twice_raises(
        self, started_session: InterviewSession
    ) -> None:
        started_session.mark_interview_complete()
        with pytest.raises(SessionAlreadyCompleteError):
            started_session.mark_interview_complete()

    def test_is_complete_initially_false(self, session: InterviewSession) -> None:
        assert session.is_complete() is False


# ══════════════════════════════════════════════════════════════════════════════
# Navigation – current day
# ══════════════════════════════════════════════════════════════════════════════


class TestCurrentDay:
    def test_correct_starting_day(
        self, started_session: InterviewSession
    ) -> None:
        """First day should be the first entry in the plan's selected_days."""
        day = started_session.get_current_day()
        expected = started_session.plan.selected_days[0]
        assert day.day == expected.day
        assert day.title == expected.title

    def test_get_current_day_before_start_raises(
        self, session: InterviewSession
    ) -> None:
        with pytest.raises(SessionNotStartedError):
            session.get_current_day()

    def test_get_current_day_after_complete_raises(
        self, started_session: InterviewSession
    ) -> None:
        started_session.mark_interview_complete()
        with pytest.raises(SessionAlreadyCompleteError):
            started_session.get_current_day()


# ══════════════════════════════════════════════════════════════════════════════
# Question tracking
# ══════════════════════════════════════════════════════════════════════════════


class TestQuestionTracking:
    def test_initial_question_number_is_one(
        self, started_session: InterviewSession
    ) -> None:
        assert started_session.get_current_question_number() == 1

    def test_advance_increments_counters(
        self, started_session: InterviewSession
    ) -> None:
        result = started_session.advance_question()
        assert result == 1
        assert started_session.state.current_question_in_day == 1
        assert started_session.state.total_questions_asked == 1
        assert started_session.get_current_question_number() == 2

    def test_advance_twice(self, started_session: InterviewSession) -> None:
        started_session.advance_question()
        result = started_session.advance_question()
        assert result == 2
        assert started_session.state.current_question_in_day == 2

    def test_advance_before_start_raises(
        self, session: InterviewSession
    ) -> None:
        with pytest.raises(SessionNotStartedError):
            session.advance_question()

    def test_advance_after_complete_raises(
        self, started_session: InterviewSession
    ) -> None:
        started_session.mark_interview_complete()
        with pytest.raises(SessionAlreadyCompleteError):
            started_session.advance_question()

    def test_get_question_number_before_start_raises(
        self, session: InterviewSession
    ) -> None:
        with pytest.raises(SessionNotStartedError):
            session.get_current_question_number()


# ══════════════════════════════════════════════════════════════════════════════
# Day budget enforcement
# ══════════════════════════════════════════════════════════════════════════════


class TestDayBudget:
    def test_exceeding_day_budget_raises(
        self, started_session: InterviewSession
    ) -> None:
        """Each day in the default plan has 2 questions. A third must fail."""
        started_session.advance_question()
        started_session.advance_question()
        with pytest.raises(DayBudgetExhaustedError):
            started_session.advance_question()

    def test_day_budget_resets_after_complete_day(
        self, started_session: InterviewSession
    ) -> None:
        """After completing a day, questions for the new day start from 0."""
        started_session.advance_question()
        started_session.advance_question()
        started_session.complete_day()  # move to day 2
        # Should be allowed again (new day budget).
        started_session.advance_question()
        assert started_session.state.current_question_in_day == 1


# ══════════════════════════════════════════════════════════════════════════════
# Total question budget enforcement
# ══════════════════════════════════════════════════════════════════════════════


class TestTotalBudget:
    def test_total_budget_exhaustion(self) -> None:
        """Drive through ALL questions; the next attempt must raise."""
        plan = _make_plan()  # 4 days × 2 = 8 total
        session = InterviewSession(plan)
        session.start_session()

        # Ask all 8 questions across 4 days.
        for day_idx in range(4):
            session.advance_question()
            session.advance_question()
            if day_idx < 3:
                session.complete_day()

        assert session.total_questions_asked == 8

        # Budget is exhausted — cannot ask more.
        with pytest.raises(
            (DayBudgetExhaustedError, QuestionBudgetExhaustedError)
        ):
            session.advance_question()


# ══════════════════════════════════════════════════════════════════════════════
# Day progression
# ══════════════════════════════════════════════════════════════════════════════


class TestDayProgression:
    def test_complete_day_returns_next_day(
        self, started_session: InterviewSession
    ) -> None:
        next_day = started_session.complete_day()
        assert next_day is not None
        expected_second = started_session.plan.selected_days[1]
        assert next_day.day == expected_second.day

    def test_complete_day_adds_to_completed_list(
        self, started_session: InterviewSession
    ) -> None:
        first_day = started_session.get_current_day()
        started_session.complete_day()
        assert first_day.day in started_session.completed_days

    def test_complete_day_resets_question_counter(
        self, started_session: InterviewSession
    ) -> None:
        started_session.advance_question()
        started_session.complete_day()
        assert started_session.state.current_question_in_day == 0

    def test_complete_last_day_marks_interview_done(self) -> None:
        """Completing the final day should auto-complete the interview."""
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()

        # Advance through all 4 days.
        for _ in range(4):
            result = session.complete_day()

        assert result is None  # no next day
        assert session.is_complete() is True
        assert session.state.completed_at is not None

    def test_complete_day_before_start_raises(
        self, session: InterviewSession
    ) -> None:
        with pytest.raises(SessionNotStartedError):
            session.complete_day()

    def test_complete_day_after_interview_complete_raises(
        self, started_session: InterviewSession
    ) -> None:
        started_session.mark_interview_complete()
        with pytest.raises(SessionAlreadyCompleteError):
            started_session.complete_day()


# ══════════════════════════════════════════════════════════════════════════════
# Interview completion detection
# ══════════════════════════════════════════════════════════════════════════════


class TestCompletionDetection:
    def test_auto_complete_after_all_days(self) -> None:
        plan = _make_plan([(10, 2), (20, 2), (30, 2), (31, 2)])
        session = InterviewSession(plan)
        session.start_session()

        for i in range(4):
            session.advance_question()
            session.advance_question()
            session.complete_day()

        assert session.is_complete()
        assert len(session.completed_days) == 4
        assert session.total_questions_asked == 8

    def test_explicit_complete_before_all_days(
        self, started_session: InterviewSession
    ) -> None:
        """Engine can cut short the interview via mark_interview_complete()."""
        started_session.advance_question()
        started_session.mark_interview_complete()
        assert started_session.is_complete()
        assert started_session.total_questions_asked == 1


# ══════════════════════════════════════════════════════════════════════════════
# Conversation history
# ══════════════════════════════════════════════════════════════════════════════


class TestConversationHistory:
    def test_add_entry_returns_entry(
        self, started_session: InterviewSession
    ) -> None:
        entry = started_session.add_conversation_entry(
            role="interviewer", content="What is a vector database?"
        )
        assert isinstance(entry, ConversationEntry)
        assert entry.role == "interviewer"
        assert entry.turn_number == 1

    def test_add_multiple_entries_increments_turn(
        self, started_session: InterviewSession
    ) -> None:
        started_session.add_conversation_entry("interviewer", "Q1")
        e2 = started_session.add_conversation_entry("candidate", "A1")
        e3 = started_session.add_conversation_entry("interviewer", "Q2")
        assert e2.turn_number == 2
        assert e3.turn_number == 3

    def test_entry_records_current_day(
        self, started_session: InterviewSession
    ) -> None:
        current_day = started_session.get_current_day()
        entry = started_session.add_conversation_entry("interviewer", "Q")
        assert entry.curriculum_day == current_day.day

    def test_get_history_returns_all_entries(
        self, started_session: InterviewSession
    ) -> None:
        started_session.add_conversation_entry("interviewer", "Q1")
        started_session.add_conversation_entry("candidate", "A1")
        history = started_session.get_conversation_history()
        assert len(history) == 2

    def test_add_entry_before_start_raises(
        self, session: InterviewSession
    ) -> None:
        with pytest.raises(SessionNotStartedError):
            session.add_conversation_entry("interviewer", "Q")

    def test_history_is_copy(
        self, started_session: InterviewSession
    ) -> None:
        """get_conversation_history should return a copy, not a reference."""
        started_session.add_conversation_entry("interviewer", "Q1")
        h1 = started_session.get_conversation_history()
        h2 = started_session.get_conversation_history()
        assert h1 is not h2


# ══════════════════════════════════════════════════════════════════════════════
# Full session walkthrough – state consistency
# ══════════════════════════════════════════════════════════════════════════════


class TestFullWalkthrough:
    """Drive a session through a complete interview and verify all state."""

    def test_full_interview_lifecycle(self) -> None:
        plan = _make_plan([(10, 2), (20, 3), (25, 2), (30, 1)])  # total = 8
        session = InterviewSession(plan)

        # ── Pre-start checks ──────────────────────────────────────────────────
        assert not session.is_complete()
        assert session.state.interview_started is False

        # ── Start ─────────────────────────────────────────────────────────────
        session.start_session()
        assert session.state.interview_started is True
        assert session.get_current_day().day == 10
        assert session.get_current_question_number() == 1

        # ── Day 10 (2 questions) ──────────────────────────────────────────────
        session.add_conversation_entry("interviewer", "Q1")
        session.advance_question()
        session.add_conversation_entry("candidate", "A1")
        session.add_conversation_entry("interviewer", "Q2")
        session.advance_question()
        session.add_conversation_entry("candidate", "A2")
        assert session.total_questions_asked == 2
        next_day = session.complete_day()
        assert next_day is not None
        assert next_day.day == 20

        # ── Day 20 (3 questions) ──────────────────────────────────────────────
        for i in range(3):
            session.advance_question()
        assert session.total_questions_asked == 5
        next_day = session.complete_day()
        assert next_day is not None
        assert next_day.day == 25

        # ── Day 25 (2 questions) ──────────────────────────────────────────────
        session.advance_question()
        session.advance_question()
        assert session.total_questions_asked == 7
        next_day = session.complete_day()
        assert next_day is not None
        assert next_day.day == 30

        # ── Day 30 (1 question) — final day ──────────────────────────────────
        session.advance_question()
        assert session.total_questions_asked == 8
        result = session.complete_day()
        assert result is None  # no more days

        # ── Post-interview checks ─────────────────────────────────────────────
        assert session.is_complete()
        assert session.completed_days == [10, 20, 25, 30]
        assert session.total_questions_asked == 8
        assert len(session.get_conversation_history()) == 4  # Q1,A1,Q2,A2

        # Cannot ask more questions.
        with pytest.raises(SessionAlreadyCompleteError):
            session.advance_question()
