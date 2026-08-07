"""
tests/test_session_registry.py
-------------------------------
Unit tests for app.services.session_registry.
"""

from __future__ import annotations

import pytest

from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.services.interview_session import InterviewSession
from app.services.session_registry import (
    DuplicateSessionError,
    SessionNotFoundError,
    SessionRegistry,
    get_session_registry,
)


def _make_selected_day(day: int) -> SelectedDay:
    return SelectedDay(
        day=day,
        title=f"Day {day} Topic",
        module_number=1,
        module_title="Module 1",
        type="BUILD",
        tools=["ToolA"],
        objectives=["Objective A"],
        selection_reason="Test reason",
        priority=1,
        planned_questions=2,
    )


def _make_plan() -> InterviewPlan:
    days = [
        _make_selected_day(10),
        _make_selected_day(15),
        _make_selected_day(20),
        _make_selected_day(25),
    ]
    return InterviewPlan(
        candidate_id="CAND-001",
        candidate_name="Alex Smith",
        selected_days=days,
        selected_modules=["Module 1"],
        planned_question_count=8,
        questions_per_day={10: 2, 15: 2, 20: 2, 25: 2},
        initial_difficulty="Medium",
        evaluation_goals=["Technical Depth"],
        interview_strategy="Direct assessment.",
        selection_reasons={10: "Reason", 15: "Reason", 20: "Reason", 25: "Reason"},
    )


class TestSessionRegistry:
    @pytest.fixture()
    def registry(self) -> SessionRegistry:
        return SessionRegistry()

    def test_create_and_get_session(self, registry: SessionRegistry) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        sid = registry.create_session(session)

        assert sid == session.session_id
        assert registry.session_exists(sid) is True
        retrieved = registry.get_session(sid)
        assert retrieved is session

    def test_duplicate_session_rejection(self, registry: SessionRegistry) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        registry.create_session(session)

        with pytest.raises(DuplicateSessionError, match="already exists"):
            registry.create_session(session)

    def test_failed_lookup_raises_not_found(self, registry: SessionRegistry) -> None:
        with pytest.raises(SessionNotFoundError, match="No active session found"):
            registry.get_session("non-existent-session-id")

    def test_session_exists_returns_false_for_unknown(self, registry: SessionRegistry) -> None:
        assert registry.session_exists("unknown-id") is False

    def test_remove_session(self, registry: SessionRegistry) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        sid = registry.create_session(session)

        assert registry.session_exists(sid) is True
        registry.remove_session(sid)
        assert registry.session_exists(sid) is False

        with pytest.raises(SessionNotFoundError):
            registry.get_session(sid)

    def test_remove_non_existent_session_raises(self, registry: SessionRegistry) -> None:
        with pytest.raises(SessionNotFoundError, match="Cannot remove"):
            registry.remove_session("ghost-id")

    def test_active_session_count_and_list(self, registry: SessionRegistry) -> None:
        assert registry.active_session_count() == 0
        assert registry.list_active_sessions() == []

        s1 = InterviewSession(_make_plan())
        s2 = InterviewSession(_make_plan())

        registry.create_session(s1)
        registry.create_session(s2)

        assert registry.active_session_count() == 2
        active_ids = registry.list_active_sessions()
        assert len(active_ids) == 2
        assert s1.session_id in active_ids
        assert s2.session_id in active_ids

    def test_clear_registry(self, registry: SessionRegistry) -> None:
        s1 = InterviewSession(_make_plan())
        s2 = InterviewSession(_make_plan())
        registry.create_session(s1)
        registry.create_session(s2)

        assert registry.active_session_count() == 2
        registry.clear()
        assert registry.active_session_count() == 0
        assert registry.list_active_sessions() == []

    def test_singleton_accessor(self) -> None:
        reg1 = get_session_registry()
        reg2 = get_session_registry()
        assert reg1 is reg2
