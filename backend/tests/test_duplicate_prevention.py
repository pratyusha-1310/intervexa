"""
tests/test_duplicate_prevention.py
----------------------------------
Unit and integration tests for duplicate question prevention and follow-up limits.
"""

from __future__ import annotations

import pytest

from app.schemas.interview_decision import DecisionAction
from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.services.interview_agent import BaseLLMProvider, generate_agent_response
from app.services.interview_decision_engine import make_decision
from app.services.interview_session import InterviewSession


def _make_selected_day(day: int, objectives: list[str] = None) -> SelectedDay:
    return SelectedDay(
        day=day,
        title=f"Day {day} Topic",
        module_number=1,
        module_title="Module 1",
        type="BUILD",
        tools=["ToolA"],
        objectives=objectives or ["Objective A"],
        selection_reason="Test reason",
        priority=1,
        planned_questions=2,
    )


def _make_plan() -> InterviewPlan:
    days = [
        _make_selected_day(10, ["Optimize embeddings"]),
        _make_selected_day(15, ["Manage database partitions"]),
        _make_selected_day(20, ["Deploy Kubernetes"]),
        _make_selected_day(25, ["Log exceptions"]),
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


class ConstantLLMProvider(BaseLLMProvider):
    """LLM provider that always returns the exact same string."""

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.call_count = 0

    def generate(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        self.call_count += 1
        return self.response_text


class TestFollowUpLimitAndDuplicatePrevention:
    def test_follow_up_limited_to_at_most_one_per_question(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        
        # Day 10 has 1 question asked initially
        session.advance_question()
        session.add_conversation_entry("interviewer", "What is an embedding?")
        
        # 1. Candidate gives a very short answer
        session.add_conversation_entry("candidate", "idk")
        
        # Make decision: should be FOLLOW_UP since it's the first time
        d1 = make_decision(plan, session, candidate_answer="idk")
        assert d1.action == DecisionAction.FOLLOW_UP
        
        # Register the follow-up question
        session.add_conversation_entry("interviewer", "Can you explain it a bit more?")
        
        # 2. Candidate gives another short answer
        session.add_conversation_entry("candidate", "still idk")
        
        # Make decision: should NOT be FOLLOW_UP since we already followed up on this question.
        # It should progress to the next planned question (NEXT_QUESTION).
        d2 = make_decision(plan, session, candidate_answer="still idk")
        assert d2.action == DecisionAction.NEXT_QUESTION
        assert d2.target_day == 10

    def test_duplicate_replies_trigger_fallback(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        
        session.advance_question()
        # Add a question to conversation history
        dup_text = "How do you optimize embeddings?"
        session.add_conversation_entry("interviewer", dup_text)
        
        # Set up a provider that returns the duplicate text
        provider = ConstantLLMProvider(dup_text)
        
        decision = make_decision(plan, session, candidate_answer="Good answer details...")
        
        # Generate response: agent should detect duplicate, retry, and use the fallback question
        response = generate_agent_response(plan, session, decision, provider=provider)
        
        # Verifies the returned question is the fallback, not the duplicate
        assert response.reply != dup_text
        assert "Optimize embeddings" in response.reply
        assert provider.call_count == 2  # Initial call + retry call
