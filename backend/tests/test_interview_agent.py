"""
tests/test_interview_agent.py
------------------------------
Unit tests for app.services.interview_agent.
"""

from __future__ import annotations

import pytest

from app.schemas.interview_agent import AgentResponse
from app.schemas.interview_decision import DecisionAction, InterviewDecision
from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.services.interview_agent import (
    BaseLLMProvider,
    MockLLMProvider,
    SYSTEM_PROMPT,
    generate_agent_response,
)
from app.services.interview_session import InterviewSession


class CustomTestLLMProvider(BaseLLMProvider):
    """Custom mock provider to test LLM abstraction."""

    def __init__(self, response_text: str = "Custom mock response") -> None:
        self.response_text = response_text
        self.call_count = 0
        self.last_system_prompt = ""
        self.last_messages = []

    def generate(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_messages = messages
        return self.response_text


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


class TestAgentResponseModel:
    def test_agent_response_fields(self) -> None:
        resp = AgentResponse(
            reply="Hello! Let's get started.",
            current_day=10,
            current_topic="Day 10 Topic",
            follow_up=False,
        )
        assert resp.reply == "Hello! Let's get started."
        assert resp.current_day == 10
        assert resp.current_topic == "Day 10 Topic"
        assert resp.follow_up is False


class TestProviderAbstraction:
    def test_custom_provider_invoked(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        decision = InterviewDecision(
            action=DecisionAction.NEXT_QUESTION,
            reason="Starting interview",
            target_day=10,
            follow_up_required=False,
            interview_complete=False,
        )

        provider = CustomTestLLMProvider("What is FastAPI?")
        response = generate_agent_response(plan, session, decision, provider=provider)

        assert provider.call_count == 1
        assert provider.last_system_prompt == SYSTEM_PROMPT
        assert response.reply == "What is FastAPI?"
        assert response.current_day == 10
        assert response.current_topic == "Day 10 Topic"
        assert response.follow_up is False


class TestQuestionGenerationScenarios:
    def test_opening_question_generation(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        decision = InterviewDecision(
            action=DecisionAction.NEXT_QUESTION,
            reason="First question",
            target_day=10,
            follow_up_required=False,
            interview_complete=False,
        )

        response = generate_agent_response(plan, session, decision, provider=MockLLMProvider())

        assert isinstance(response, AgentResponse)
        assert response.reply != ""
        assert response.current_day == 10
        assert response.current_topic == "Day 10 Topic"
        assert response.follow_up is False

    def test_follow_up_generation(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        session.advance_question()
        decision = InterviewDecision(
            action=DecisionAction.FOLLOW_UP,
            reason="Answer too short",
            target_day=10,
            follow_up_required=True,
            interview_complete=False,
        )

        response = generate_agent_response(plan, session, decision, provider=MockLLMProvider())

        assert isinstance(response, AgentResponse)
        assert response.follow_up is True
        assert "elaborate" in response.reply.lower() or "edge cases" in response.reply.lower()

    def test_next_topic_generation(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        decision = InterviewDecision(
            action=DecisionAction.NEXT_DAY,
            reason="Transition to Day 15",
            target_day=15,
            follow_up_required=False,
            interview_complete=False,
        )

        response = generate_agent_response(plan, session, decision, provider=MockLLMProvider())

        assert isinstance(response, AgentResponse)
        assert response.current_day == 15
        assert response.current_topic == "Day 15 Topic"
        assert response.follow_up is False

    def test_interview_completion_message(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        decision = InterviewDecision(
            action=DecisionAction.END_INTERVIEW,
            reason="Budget reached",
            target_day=None,
            follow_up_required=False,
            interview_complete=True,
        )

        response = generate_agent_response(plan, session, decision, provider=MockLLMProvider())

        assert isinstance(response, AgentResponse)
        assert response.current_day is None
        assert response.current_topic is None
        assert "Thank you" in response.reply

    def test_deterministic_behaviour_under_mock(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        decision = InterviewDecision(
            action=DecisionAction.NEXT_QUESTION,
            reason="Next question",
            target_day=10,
            follow_up_required=False,
            interview_complete=False,
        )

        mock_provider = MockLLMProvider({"topic": "Deterministic question text"})
        resp1 = generate_agent_response(plan, session, decision, provider=mock_provider)
        resp2 = generate_agent_response(plan, session, decision, provider=mock_provider)

        assert resp1.reply == resp2.reply
        assert resp1.current_day == resp2.current_day
