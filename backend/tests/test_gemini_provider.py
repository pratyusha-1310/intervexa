"""
tests/test_gemini_provider.py
------------------------------
Unit tests for GeminiLLMProvider and provider selection logic.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.interview_agent import AgentResponse
from app.schemas.interview_decision import DecisionAction, InterviewDecision
from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.services.interview_agent import (
    BaseLLMProvider,
    GeminiLLMProvider,
    MockLLMProvider,
    OpenAILLMProvider,
    generate_agent_response,
    get_default_provider,
)
from app.services.interview_session import InterviewSession


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


class TestProviderSelection:
    def test_provider_selection_gemini(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}):
            provider = get_default_provider()
            assert isinstance(provider, GeminiLLMProvider)

    def test_provider_selection_openai(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            provider = get_default_provider()
            assert isinstance(provider, OpenAILLMProvider)

    def test_provider_selection_mock(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "mock"}):
            provider = get_default_provider()
            assert isinstance(provider, MockLLMProvider)

    def test_provider_selection_fallback(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "unknown_provider"}):
            provider = get_default_provider()
            assert isinstance(provider, MockLLMProvider)


class TestGeminiLLMProvider:
    def test_gemini_initialization(self) -> None:
        provider = GeminiLLMProvider(api_key="test_key", model="gemini-2.5-flash")
        assert provider.api_key == "test_key"
        assert provider.model == "gemini-2.5-flash"

    def test_missing_api_key_falls_back_to_mock(self) -> None:
        provider = GeminiLLMProvider(api_key="")
        result = provider.generate("system prompt", [{"role": "user", "content": "hello"}])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gemini_generate_successful_with_mocked_sdk(self) -> None:
        expected_text = "Generated Gemini interviewer question"

        mock_response = MagicMock()
        mock_response.text = expected_text

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response

        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client_instance

        mock_google = MagicMock()
        mock_google.genai = mock_genai

        mock_types = MagicMock()

        provider = GeminiLLMProvider(api_key="valid_key", model="gemini-2.5-flash")

        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai, "google.genai.types": mock_types}):
            with patch("app.services.interview_agent.MockLLMProvider.generate") as mock_fallback:
                result = provider.generate("System prompt", [{"role": "user", "content": "Question"}])
                assert result == expected_text
                mock_fallback.assert_not_called()

    def test_gemini_generate_error_falls_back(self) -> None:
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = Exception("API Quota Exceeded")

        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client_instance

        mock_google = MagicMock()
        mock_google.genai = mock_genai

        provider = GeminiLLMProvider(api_key="valid_key", model="gemini-2.5-flash")

        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = provider.generate("System prompt", [{"role": "user", "content": "Question"}])
            assert isinstance(result, str)
            assert len(result) > 0

    def test_interview_agent_compatibility_with_gemini(self) -> None:
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

        expected_text = "Gemini question: Can you explain vector databases?"
        mock_response = MagicMock()
        mock_response.text = expected_text

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response

        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client_instance

        mock_google = MagicMock()
        mock_google.genai = mock_genai

        provider = GeminiLLMProvider(api_key="valid_key")

        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            agent_resp = generate_agent_response(plan, session, decision, provider=provider)
            assert isinstance(agent_resp, AgentResponse)
            assert agent_resp.reply == expected_text
            assert agent_resp.current_day == 10
            assert agent_resp.current_topic == "Day 10 Topic"
