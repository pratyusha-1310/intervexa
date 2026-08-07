"""
tests/test_interview_decision_engine.py
----------------------------------------
Unit tests for app.services.interview_decision_engine.
"""

from __future__ import annotations

import pytest

from app.schemas.interview_decision import DecisionAction, InterviewDecision
from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.services.interview_decision_engine import (
    _is_short_or_incomplete_answer,
    make_decision,
)
from app.services.interview_session import InterviewSession


def _make_selected_day(day: int, planned_questions: int = 2) -> SelectedDay:
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
        planned_questions=planned_questions,
    )


def _make_plan() -> InterviewPlan:
    days = [_make_selected_day(10, 2), _make_selected_day(15, 2), _make_selected_day(20, 2), _make_selected_day(25, 2)]
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


class TestDecisionModelValidation:
    def test_decision_model_validates_fields(self) -> None:
        decision = InterviewDecision(
            action=DecisionAction.NEXT_QUESTION,
            reason="Testing",
            target_day=10,
            follow_up_required=False,
            interview_complete=False,
        )
        assert decision.action == DecisionAction.NEXT_QUESTION
        assert decision.reason == "Testing"
        assert decision.target_day == 10
        assert decision.follow_up_required is False
        assert decision.interview_complete is False

    def test_enum_values(self) -> None:
        assert DecisionAction.FOLLOW_UP.value == "FOLLOW_UP"
        assert DecisionAction.NEXT_QUESTION.value == "NEXT_QUESTION"
        assert DecisionAction.NEXT_DAY.value == "NEXT_DAY"
        assert DecisionAction.END_INTERVIEW.value == "END_INTERVIEW"


class TestFollowUpHeuristics:
    def test_short_answer_triggers_incomplete(self) -> None:
        is_inc, reason = _is_short_or_incomplete_answer("It is okay.")
        assert is_inc is True
        assert "too short" in reason

    def test_evasive_phrase_triggers_incomplete(self) -> None:
        is_inc, reason = _is_short_or_incomplete_answer("I don't know")
        assert is_inc is True
        assert "evasive" in reason

    def test_adequate_answer_is_not_incomplete(self) -> None:
        answer = (
            "Vector databases index high-dimensional embeddings using algorithms like HNSW "
            "to enable fast approximate nearest neighbor search across text and image data."
        )
        is_inc, _ = _is_short_or_incomplete_answer(answer)
        assert is_inc is False


class TestDecisionEngineLogic:
    def test_follow_up_decision_when_answer_too_short(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        session.advance_question()  # asked question 1 on day 10

        decision = make_decision(plan, session, candidate_answer="Short answer.")

        assert decision.action == DecisionAction.FOLLOW_UP
        assert decision.follow_up_required is True
        assert decision.target_day == 10
        assert decision.interview_complete is False

    def test_next_question_decision_when_good_answer(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        session.advance_question()  # 1 question in day 10 (quota is 2)

        good_answer = (
            "FastAPI uses Pydantic for data validation and async endpoints powered by Starlette and Uvicorn "
            "to deliver high-performance asynchronous API web services in Python."
        )
        decision = make_decision(plan, session, candidate_answer=good_answer)

        assert decision.action == DecisionAction.NEXT_QUESTION
        assert decision.follow_up_required is False
        assert decision.target_day == 10
        assert decision.interview_complete is False

    def test_next_day_decision_when_current_day_quota_reached(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        # Day 10 quota is 2 questions
        session.advance_question()
        session.advance_question()

        good_answer = (
            "FastAPI uses Pydantic for data validation and async endpoints powered by Starlette and Uvicorn "
            "to deliver high-performance asynchronous API web services in Python."
        )
        decision = make_decision(plan, session, candidate_answer=good_answer)

        assert decision.action == DecisionAction.NEXT_DAY
        assert decision.target_day == 15
        assert decision.interview_complete is False

    def test_end_interview_when_total_budget_reached(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        # Force total_questions_asked to total planned (8)
        session._state.total_questions_asked = 8

        decision = make_decision(plan, session, candidate_answer="Some answer")

        assert decision.action == DecisionAction.END_INTERVIEW
        assert decision.interview_complete is True
        assert decision.target_day is None

    def test_end_interview_when_session_marked_complete(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        session.mark_interview_complete()

        decision = make_decision(plan, session)

        assert decision.action == DecisionAction.END_INTERVIEW
        assert decision.interview_complete is True

    def test_deterministic_behavior(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        session.advance_question()

        answer = "This is a brief response."
        dec1 = make_decision(plan, session, answer)
        dec2 = make_decision(plan, session, answer)

        assert dec1.action == dec2.action
        assert dec1.reason == dec2.reason
        assert dec1.target_day == dec2.target_day
