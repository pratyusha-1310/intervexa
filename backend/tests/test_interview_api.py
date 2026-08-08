"""
tests/test_interview_api.py
----------------------------
Integration and unit tests for POST /api/interview.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.interview_api import InterviewApiRequest, InterviewApiResponse
from app.services.interview_agent import MockLLMProvider
from app.services.interview_controller import process_interview_request
from app.services.session_registry import SessionRegistry, get_session_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Clear session registry before each test."""
    get_session_registry().clear()


class TestInterviewApiSchemas:
    def test_request_schema_aliases(self) -> None:
        req = InterviewApiRequest.model_validate({"sessionId": "sess-1", "candidate": "CAND-001"})
        assert req.session_id == "sess-1"
        assert req.candidate == "CAND-001"

    def test_response_schema_in_progress(self) -> None:
        resp = InterviewApiResponse(reply="Hello", done=False)
        d = resp.to_dict()
        assert d == {"reply": "Hello", "done": False}
        assert "feedback" not in d

    def test_response_schema_completed(self) -> None:
        resp = InterviewApiResponse(reply="Done!", done=True)
        d = resp.to_dict()
        assert d == {"reply": "Done!", "done": True, "feedback": None}


class TestInterviewControllerUnit:
    def test_start_interview_flow(self) -> None:
        registry = SessionRegistry()
        mock_provider = MockLLMProvider()

        req = InterviewApiRequest(sessionId="sess-test-1", candidate="CAND-001")
        res = process_interview_request(req, registry=registry, provider=mock_provider)

        assert res["done"] is False
        assert "reply" in res
        assert registry.session_exists("sess-test-1") is True

        session = registry.get_session("sess-test-1")
        assert session.candidate_id == "CAND-001"
        assert session.total_questions_asked == 1

    def test_continue_interview_flow(self) -> None:
        registry = SessionRegistry()
        mock_provider = MockLLMProvider()

        # 1. Start interview
        start_req = InterviewApiRequest(sessionId="sess-test-2", candidate="CAND-001")
        process_interview_request(start_req, registry=registry, provider=mock_provider)

        # 2. Continue interview
        cont_req = InterviewApiRequest(
            sessionId="sess-test-2",
            message="Vector databases use ANN algorithms to index embeddings efficiently.",
        )
        res = process_interview_request(cont_req, registry=registry, provider=mock_provider)

        assert "reply" in res
        session = registry.get_session("sess-test-2")
        history = session.get_conversation_history()
        assert len(history) >= 3  # interviewer Q1, candidate A1, interviewer Q2

    def test_duplicate_session_raises(self) -> None:
        registry = SessionRegistry()
        mock_provider = MockLLMProvider()

        req = InterviewApiRequest(sessionId="sess-dup", candidate="CAND-001")
        process_interview_request(req, registry=registry, provider=mock_provider)

        with pytest.raises(Exception):  # DuplicateSessionError
            process_interview_request(req, registry=registry, provider=mock_provider)

    def test_invalid_payload_raises(self) -> None:
        registry = SessionRegistry()
        req = InterviewApiRequest()

        with pytest.raises(ValueError, match="Invalid request payload"):
            process_interview_request(req, registry=registry)


class TestInterviewApiRouterIntegration:
    def test_http_start_and_continue_interview_success(self) -> None:
        # 1. Start interview
        start_payload = {
            "sessionId": "http-sess-100",
            "candidate": "CAND-001",
        }
        res_start = client.post("/api/interview", json=start_payload)
        assert res_start.status_code == 200
        data_start = res_start.json()
        assert data_start["done"] is False
        assert "reply" in data_start

        # 2. Continue interview
        cont_payload = {
            "sessionId": "http-sess-100",
            "message": "FastAPI is a modern web framework built on Starlette and Pydantic.",
        }
        res_cont = client.post("/api/interview", json=cont_payload)
        assert res_cont.status_code == 200
        data_cont = res_cont.json()
        assert "reply" in data_cont

    def test_http_candidate_not_found_returns_404(self) -> None:
        payload = {
            "sessionId": "http-sess-404",
            "candidate": "CAND-NONEXISTENT-999",
        }
        res = client.post("/api/interview", json=payload)
        assert res.status_code == 404

    def test_http_session_not_found_returns_404(self) -> None:
        payload = {
            "sessionId": "non-existent-session-id",
            "message": "Hello",
        }
        res = client.post("/api/interview", json=payload)
        assert res.status_code == 404

    def test_http_duplicate_session_returns_409(self) -> None:
        payload = {
            "sessionId": "http-sess-dup",
            "candidate": "CAND-001",
        }
        r1 = client.post("/api/interview", json=payload)
        assert r1.status_code == 200

        r2 = client.post("/api/interview", json=payload)
        assert r2.status_code == 409

    def test_http_invalid_payload_returns_400(self) -> None:
        res = client.post("/api/interview", json={})
        assert res.status_code == 400

    def test_http_complete_interview_flow(self) -> None:
        """Drive session to completion through HTTP requests."""
        sid = "http-sess-complete"
        # Start
        client.post("/api/interview", json={"sessionId": sid, "candidate": "CAND-001"})

        # Continue with detailed answers until complete
        good_answer = (
            "Vector embeddings map semantic meanings into high-dimensional vector spaces "
            "allowing similarity searches via cosine distance and HNSW indexing."
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
        assert "summary" in final_resp["feedback"]
        assert "overall_assessment" in final_resp["feedback"]
