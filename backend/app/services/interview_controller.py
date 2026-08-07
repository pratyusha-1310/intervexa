"""
interview_controller.py (service)
----------------------------------
Orchestration controller for the official POST /api/interview endpoint.

Responsibility
~~~~~~~~~~~~~~
Coordinates the workflow between request validation, loaders, planner,
session manager, session registry, decision engine, and AI interview agent.

This keeps the FastAPI router lightweight and decouples HTTP concerns from business logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.loaders.candidate_loader import CandidateNotFoundError, get_candidate
from app.loaders.curriculum_loader import load_curriculum
from app.schemas.interview_api import InterviewApiRequest, InterviewApiResponse
from app.schemas.interview_decision import DecisionAction
from app.services.interview_agent import BaseLLMProvider, generate_agent_response
from app.services.interview_decision_engine import make_decision
from app.services.interview_planner import build_interview_plan
from app.services.interview_session import InterviewSession
from app.services.session_registry import (
    DuplicateSessionError,
    SessionNotFoundError,
    SessionRegistry,
    get_session_registry,
)


def extract_candidate_id(candidate_input: Any) -> str:
    """Extracts a candidate ID string from string or dict candidate payloads."""
    if isinstance(candidate_input, str) and candidate_input.strip():
        return candidate_input.strip()
    if isinstance(candidate_input, dict):
        if "id" in candidate_input and isinstance(candidate_input["id"], str):
            return candidate_input["id"].strip()
        if "member" in candidate_input and isinstance(candidate_input["member"], dict):
            mem_id = candidate_input["member"].get("id")
            if isinstance(mem_id, str) and mem_id.strip():
                return mem_id.strip()
        if "candidate_id" in candidate_input and isinstance(candidate_input["candidate_id"], str):
            return candidate_input["candidate_id"].strip()
    raise ValueError(
        "Invalid candidate format. Must be a valid candidate ID string or object containing 'id'."
    )


def process_interview_request(
    request: InterviewApiRequest,
    registry: Optional[SessionRegistry] = None,
    provider: Optional[BaseLLMProvider] = None,
) -> Dict[str, Any]:
    """
    Orchestrates an incoming POST /api/interview request.

    Args:
        request: Validated InterviewApiRequest payload.
        registry: Optional SessionRegistry override (defaults to global singleton).
        provider: Optional BaseLLMProvider override for AI agent.

    Returns:
        Serialised response dictionary matching official spec.
    """
    active_registry = registry or get_session_registry()

    # Determine mode: Start Interview vs Continue Interview
    is_start_mode = request.candidate is not None

    if is_start_mode:
        return _handle_start_interview(request, active_registry, provider)
    elif request.session_id and request.message is not None:
        return _handle_continue_interview(request, active_registry, provider)
    else:
        raise ValueError(
            "Invalid request payload. Must provide either 'candidate' to start an interview "
            "or 'sessionId' and 'message' to continue an interview."
        )


def _handle_start_interview(
    request: InterviewApiRequest,
    registry: SessionRegistry,
    provider: Optional[BaseLLMProvider],
) -> Dict[str, Any]:
    """Handles Start Interview flow."""
    candidate_id = extract_candidate_id(request.candidate)

    # Load candidate and curriculum data
    candidate_data = get_candidate(candidate_id)
    curriculum_data = load_curriculum()

    # Generate InterviewPlan
    plan = build_interview_plan(candidate_data, curriculum_data)

    # Initialize InterviewSession
    session = InterviewSession(plan, session_id=request.session_id)
    session.start_session()

    # Register session in memory
    registry.create_session(session)

    # Generate opening interviewer message
    decision = make_decision(plan, session, candidate_answer=None)
    agent_response = generate_agent_response(plan, session, decision, provider=provider)

    # Advance question counter & record entry
    session.advance_question()
    session.add_conversation_entry("interviewer", agent_response.reply)

    response = InterviewApiResponse(reply=agent_response.reply, done=False)
    return response.to_dict()


def _handle_continue_interview(
    request: InterviewApiRequest,
    registry: SessionRegistry,
    provider: Optional[BaseLLMProvider],
) -> Dict[str, Any]:
    """Handles Continue Interview flow."""
    session_id = request.session_id
    if not session_id:
        raise ValueError("Missing 'sessionId' in continue interview request.")

    # Retrieve session from registry
    session = registry.get_session(session_id)
    plan = session.plan

    # Check if already complete
    if session.is_complete():
        response = InterviewApiResponse(
            reply="The interview session has already been completed.",
            done=True,
            feedback=None,
        )
        return response.to_dict()

    # Record candidate message
    candidate_msg = request.message or ""
    session.add_conversation_entry("candidate", candidate_msg)

    # Make decision based on session, plan, and candidate message
    decision = make_decision(plan, session, candidate_answer=candidate_msg)

    # Execute decision action on session state
    if decision.action == DecisionAction.NEXT_DAY:
        session.complete_day()
        if not session.is_complete():
            session.advance_question()
    elif decision.action == DecisionAction.NEXT_QUESTION:
        session.advance_question()
    elif decision.action == DecisionAction.FOLLOW_UP:
        pass  # Stay on current question turn for follow up
    elif decision.action == DecisionAction.END_INTERVIEW:
        if not session.is_complete():
            session.mark_interview_complete()

    # Generate AI interviewer response
    agent_response = generate_agent_response(plan, session, decision, provider=provider)

    # Record interviewer response
    session.add_conversation_entry("interviewer", agent_response.reply)

    is_done = decision.interview_complete or session.is_complete()

    response = InterviewApiResponse(
        reply=agent_response.reply,
        done=is_done,
        feedback=None if is_done else None,
    )
    return response.to_dict()
