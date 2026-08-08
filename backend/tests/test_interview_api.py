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


class TestCandidatePayloadFix:
    @pytest.fixture(autouse=True)
    def _reset_registry(self) -> None:
        get_session_registry().clear()

    def test_start_with_existing_candidate_id(self) -> None:
        payload = {
            "sessionId": "existing-id-sess",
            "candidate": "CAND-001"
        }
        res = client.post("/api/interview", json=payload)
        assert res.status_code == 200
        assert get_session_registry().session_exists("existing-id-sess") is True
        session = get_session_registry().get_session("existing-id-sess")
        assert session.candidate_id == "CAND-001"

    def test_start_with_custom_candidate_profile_not_in_json(self) -> None:
        custom_candidate = {
            "member": {
                "id": "cand-custom-01",
                "name": "Custom Engineering Candidate",
                "yearsExperience": 6
            },
            "missions": [
                { "day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 1 },
                { "day": 8, "title": "Vector Databases Overview", "passed": True, "attempts": 1 },
                { "day": 10, "title": "Retrieval & Matching Engine", "passed": True, "attempts": 2 },
                { "day": 12, "title": "Prompt Engineering Fundamentals", "passed": True, "attempts": 1 },
                { "day": 16, "title": "Chatbot Backend & API Integration", "passed": True, "attempts": 1 }
            ],
            "signals": {
                "missionsCompleted": 5,
                "missionsFirstTry": 4
            }
        }
        payload = {
            "sessionId": "custom-candidate-sess",
            "candidate": custom_candidate
        }
        res = client.post("/api/interview", json=payload)
        assert res.status_code == 200
        
        registry = get_session_registry()
        assert registry.session_exists("custom-candidate-sess") is True
        session = registry.get_session("custom-candidate-sess")
        
        # Verify supplied candidate ID is stored
        assert session.candidate_id == "cand-custom-01"
        
        # Verify supplied name is used in the interview plan
        assert session.plan.candidate_name == "Custom Engineering Candidate"
        # Verify initial difficulty is derived from custom candidate experience (6 years -> Medium-High)
        assert session.plan.initial_difficulty == "Medium-High"

    def test_malformed_candidate_profile_payload_rejected(self) -> None:
        # member is missing yearsExperience
        bad_candidate = {
            "member": {
                "id": "cand-bad-01",
                "name": "Broken Candidate"
            },
            "missions": [],
            "signals": {
                "missionsCompleted": 0,
                "missionsFirstTry": 0
            }
        }
        payload = {
            "sessionId": "bad-cand-sess",
            "candidate": bad_candidate
        }
        res = client.post("/api/interview", json=payload)
        assert res.status_code == 400
        assert "Malformed candidate profile" in res.json()["detail"]

    def test_complete_start_continue_flow_with_custom_candidate(self) -> None:
        custom_candidate = {
            "member": {
                "id": "cand-flow-99",
                "name": "Flow Candidate",
                "yearsExperience": 3
            },
            "missions": [
                { "day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 1 },
                { "day": 8, "title": "Vector Databases Overview", "passed": True, "attempts": 1 },
                { "day": 10, "title": "Retrieval & Matching Engine", "passed": True, "attempts": 2 },
                { "day": 12, "title": "Prompt Engineering Fundamentals", "passed": True, "attempts": 1 },
                { "day": 16, "title": "Chatbot Backend & API Integration", "passed": True, "attempts": 1 }
            ],
            "signals": {
                "missionsCompleted": 5,
                "missionsFirstTry": 4
            }
        }
        sid = "flow-sess-custom"
        
        # Start
        start_res = client.post("/api/interview", json={"sessionId": sid, "candidate": custom_candidate})
        assert start_res.status_code == 200
        
        # Continue
        cont_res = client.post("/api/interview", json={
            "sessionId": sid,
            "message": "Vector search matches similarity using distance metrics like cosine distance or dot product."
        })
        assert cont_res.status_code == 200
        assert "reply" in cont_res.json()
        assert cont_res.json()["done"] is False

