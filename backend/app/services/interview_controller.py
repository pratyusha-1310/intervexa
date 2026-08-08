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

from app.config.settings import get_settings
from app.loaders.candidate_loader import CandidateNotFoundError, get_candidate
from app.loaders.curriculum_loader import load_curriculum
from app.schemas.candidate_profile import CandidateProfile
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


def resolve_candidate(candidate_input: Any) -> Dict[str, Any]:
    """
    Validates and resolves the candidate data.
    If a complete candidate profile is provided, it is validated and used directly.
    Otherwise, extracts the ID and retrieves the profile from the candidates loader.
    """
    if candidate_input is None:
        raise ValueError("Missing 'candidate' field in start request.")

    # 1. If it's a full candidate profile dictionary, validate and return directly
    if isinstance(candidate_input, dict) and "member" in candidate_input and "missions" in candidate_input and "signals" in candidate_input:
        try:
            profile = CandidateProfile.model_validate(candidate_input)
            return profile.model_dump()
        except Exception as exc:
            raise ValueError(f"Malformed candidate profile: {exc}") from exc

    # 2. Extract candidate ID for local lookup
    candidate_id = ""
    if isinstance(candidate_input, str) and candidate_input.strip():
        candidate_id = candidate_input.strip()
    elif isinstance(candidate_input, dict):
        if "id" in candidate_input and isinstance(candidate_input["id"], str):
            candidate_id = candidate_input["id"].strip()
        elif "member" in candidate_input and isinstance(candidate_input["member"], dict):
            mem_id = candidate_input["member"].get("id")
            if isinstance(mem_id, str) and mem_id.strip():
                candidate_id = mem_id.strip()
            else:
                raise ValueError("Supplied candidate object must have a valid member.id.")
        elif "candidate_id" in candidate_input and isinstance(candidate_input["candidate_id"], str):
            candidate_id = candidate_input["candidate_id"].strip()
        else:
            raise ValueError("Malformed candidate start payload: missing candidate fields.")
    else:
        raise ValueError("Candidate field must be a candidate object or ID string.")

    if not candidate_id:
        raise ValueError("Candidate ID cannot be empty.")

    return get_candidate(candidate_id)


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
    # Resolve candidate profile from either the complete profile object or local lookup
    candidate_data = resolve_candidate(request.candidate)
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
        from app.services.interview_feedback import generate_feedback
        feedback_obj = generate_feedback(plan, session, provider=provider)
        response = InterviewApiResponse(
            reply="The interview session has already been completed.",
            done=True,
            feedback=feedback_obj,
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

    feedback_obj = None
    if is_done:
        from app.services.interview_feedback import generate_feedback
        feedback_obj = generate_feedback(plan, session, provider=provider)

    response = InterviewApiResponse(
        reply=agent_response.reply,
        done=is_done,
        feedback=feedback_obj,
    )
    return response.to_dict()
