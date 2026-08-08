"""
tests/test_interview_feedback.py
---------------------------------
Unit and integration tests for the Structured Feedback Engine.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.interview_feedback import InterviewFeedback
from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.services.interview_agent import BaseLLMProvider, MockLLMProvider
from app.services.interview_feedback import generate_feedback
from app.services.interview_session import InterviewSession
from app.services.session_registry import get_session_registry

client = TestClient(app)


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


class CustomMockLLMProvider(BaseLLMProvider):
    """Custom mock provider returning specified text."""
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    def generate(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        return self.response_text


class TestFeedbackSchema:
    def test_schema_validates_required_fields(self) -> None:
        feedback = InterviewFeedback(
            summary="Good performance",
            strengths=["FastAPI knowledge", "Pydantic usage"],
            gaps=["None identified"],
            next=["Review database optimization"],
            technical_understanding="Solid concept depth",
            reasoning="Constructive decisions made",
            communication="Clear explanation",
            overall_assessment="Strong Pass",
        )
        assert feedback.summary == "Good performance"
        assert len(feedback.strengths) == 2
        assert feedback.overall_assessment == "Strong Pass"


class TestFeedbackEngineService:
    def test_successful_feedback_generation(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        
        json_output = {
            "summary": "Alex demonstrates clear understanding of Python web frameworks.",
            "strengths": ["Clear technical communication", "Robust code design"],
            "gaps": ["Minor gaps in asynchronous DB drivers"],
            "next": ["Read up on async pg drivers"],
            "technical_understanding": "Solid depth of key structures.",
            "reasoning": "Understands scaling challenges.",
            "communication": "Fluent and clear.",
            "overall_assessment": "Pass",
        }
        
        provider = CustomMockLLMProvider(json.dumps(json_output))
        feedback = generate_feedback(plan, session, provider=provider)
        
        assert isinstance(feedback, InterviewFeedback)
        assert feedback.summary == json_output["summary"]
        assert feedback.overall_assessment == "Pass"
        assert feedback.strengths == json_output["strengths"]

    def test_feedback_generation_markdown_stripping(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()
        
        markdown_output = (
            "```json\n"
            "{\n"
            '  "summary": "Alex is great.",\n'
            '  "strengths": [],\n'
            '  "gaps": [],\n'
            '  "next": [],\n'
            '  "technical_understanding": "Good",\n'
            '  "reasoning": "Good",\n'
            '  "communication": "Good",\n'
            '  "overall_assessment": "Pass"\n'
            "}\n"
            "```"
        )
        
        provider = CustomMockLLMProvider(markdown_output)
        feedback = generate_feedback(plan, session, provider=provider)
        assert feedback.summary == "Alex is great."
        assert feedback.overall_assessment == "Pass"

    def test_fallback_on_llm_exception(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()

        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.generate.side_effect = Exception("Connection Refused")

        feedback = generate_feedback(plan, session, provider=mock_provider)
        
        assert isinstance(feedback, InterviewFeedback)
        assert "fallback" in feedback.summary.lower() or "completed" in feedback.summary.lower()
        assert "Connection Refused" in feedback.technical_understanding

    def test_fallback_on_malformed_json(self) -> None:
        plan = _make_plan()
        session = InterviewSession(plan)
        session.start_session()

        provider = CustomMockLLMProvider("Invalid raw text response that is not JSON.")
        feedback = generate_feedback(plan, session, provider=provider)
        
        assert isinstance(feedback, InterviewFeedback)
        assert "Technical evaluation requires manual review" in feedback.overall_assessment


class TestFeedbackApiIntegration:
    @pytest.fixture(autouse=True)
    def _reset_registry(self) -> None:
        get_session_registry().clear()

    def test_api_completed_flow_returns_feedback_object(self) -> None:
        sid = "feedback-http-sess"
        # 1. Start interview
        client.post("/api/interview", json={"sessionId": sid, "candidate": "CAND-001"})

        # Answer 8 times with detailed answers to conclue the interview
        good_answer = (
            "FastAPI uses async/await syntax to handle concurrent I/O operations non-blockingly, "
            "allowing it to achieve extremely high throughput comparable to NodeJS and Go."
        )

        final_resp = None
        for _ in range(15):
            r = client.post("/api/interview", json={"sessionId": sid, "message": good_answer})
            final_resp = r.json()
            if final_resp.get("done") is True:
                break

        assert final_resp is not None
        assert final_resp["done"] is True
        assert final_resp["feedback"] is not None
        
        feedback = final_resp["feedback"]
        assert "summary" in feedback
        assert isinstance(feedback["strengths"], list)
        assert "overall_assessment" in feedback
