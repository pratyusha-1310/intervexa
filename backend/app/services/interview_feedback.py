"""
interview_feedback.py (service)
-------------------------------
Structured Feedback Engine.

Responsibility
~~~~~~~~~~~~~~
Consumes the complete interview context (InterviewPlan, InterviewSession)
and uses a BaseLLMProvider to construct objective, structured feedback.

Features:
- Completely provider-agnostic.
- Structured prompt asking the model for strict JSON formatting.
- Robust exception handling that returns a safe fallback feedback object
  upon failure, guaranteeing the API always succeeds.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.schemas.interview_feedback import InterviewFeedback
from app.schemas.interview_plan import InterviewPlan
from app.services.interview_agent import BaseLLMProvider, get_default_provider
from app.services.interview_session import InterviewSession

FEEDBACK_SYSTEM_PROMPT = """You are an objective and rigorous technical evaluator. Your job is to construct a structured assessment of the candidate based on the technical interview transcript.

CRITICAL INSTRUCTIONS:
1. Respond ONLY with a valid, clean JSON object. Do not include markdown code blocks (e.g. do NOT wrap in ```json), preambles, or conversational filler.
2. Be objective, precise, and analytical. Avoid generic or overly effusive praise.
3. Base your assessment purely on the provided candidate transcript, curriculum day details, and evaluation goals.
4. Ensure the output JSON contains exactly the following fields:
{
  "summary": "Concise summary of candidate's technical capability.",
  "strengths": ["list of key strengths"],
  "gaps": ["list of knowledge gaps"],
  "next": ["list of actionable next steps"],
  "technical_understanding": "Evaluation of core technical concept depth.",
  "reasoning": "Evaluation of engineering trade-offs and decision making.",
  "communication": "Evaluation of technical communication clarity.",
  "overall_assessment": "Final summary recommendation (Pass/Weak Pass/Fail)."
}
"""


def _generate_fallback_feedback(
    plan: InterviewPlan,
    session: InterviewSession,
    error_message: str = "",
) -> InterviewFeedback:
    """Generates a safe fallback InterviewFeedback object when LLM call or parsing fails."""
    day_numbers = sorted(d.day for d in plan.selected_days)
    covered_topics = [d.title for d in plan.selected_days]
    
    return InterviewFeedback(
        summary=(
            f"Technical interview session completed for candidate '{plan.candidate_name}' ({plan.candidate_id}). "
            f"Assessed across {len(day_numbers)} curriculum areas: {', '.join(covered_topics)}."
        ),
        strengths=[
            f"Successfully engaged with questions across planned curriculum days.",
            f"Addressed concepts related to the target difficulty band ({plan.initial_difficulty}).",
        ],
        gaps=[
            "Detailed gap assessment unavailable due to automated evaluation constraint.",
        ],
        next=[
            "Review learning materials for modules: " + ", ".join(plan.selected_modules),
        ],
        technical_understanding=(
            f"Assessment covered curriculum objectives but detailed evaluation was bypassed. "
            f"Errors logged: {error_message}" if error_message else "Detailed technical depth evaluation bypassed."
        ),
        reasoning="Engineering trade-off reasoning assessment was bypassed.",
        communication="Technical communication assessment was bypassed.",
        overall_assessment="Interview completed. Technical evaluation requires manual review.",
    )


def generate_feedback(
    plan: InterviewPlan,
    session: InterviewSession,
    provider: Optional[BaseLLMProvider] = None,
) -> InterviewFeedback:
    """
    Constructs structured interview feedback based on the session details.

    Args:
        plan: The active InterviewPlan.
        session: The concluded InterviewSession.
        provider: Optional BaseLLMProvider override (defaults to default LLM provider).

    Returns:
        A validated InterviewFeedback schema object.
    """
    active_provider = provider or get_default_provider()

    # Build history context for the prompt
    history_entries = []
    for entry in session.get_conversation_history():
        role_label = "Interviewer" if entry.role == "interviewer" else "Candidate"
        history_entries.append(f"[{role_label} - Day {entry.curriculum_day}]: {entry.content}")
    history_text = "\n\n".join(history_entries)

    # Build day metadata context
    day_metadata = []
    for day in plan.selected_days:
        day_metadata.append(
            f"- Day {day.day} ('{day.title}'): Objectives: {day.objectives}. Tools: {day.tools}"
        )
    day_metadata_text = "\n".join(day_metadata)

    user_prompt = (
        f"CANDIDATE INFORMATION:\n"
        f"- ID: {plan.candidate_id}\n"
        f"- Name: {plan.candidate_name}\n"
        f"- Target Difficulty Level: {plan.initial_difficulty}\n"
        f"- Planned Question Count: {plan.planned_question_count}\n"
        f"- Evaluation Goals: {plan.evaluation_goals}\n\n"
        f"CURRICULUM CONTEXT:\n"
        f"{day_metadata_text}\n\n"
        f"INTERVIEW TRANSCRIPT:\n"
        f"{history_text}\n\n"
        f"Please perform the evaluation and return the JSON payload exactly matching the specified structure."
    )

    messages = [{"role": "user", "content": user_prompt}]

    try:
        raw_response = active_provider.generate(
            system_prompt=FEEDBACK_SYSTEM_PROMPT,
            messages=messages,
        )

        # Handle potential markdown wrapping (e.g. ```json ... ```)
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith("```"):
            lines = cleaned_response.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_response = "\n".join(lines).strip()

        parsed_json = json.loads(cleaned_response)
        
        return InterviewFeedback(
            summary=parsed_json["summary"],
            strengths=parsed_json["strengths"],
            gaps=parsed_json["gaps"],
            next=parsed_json["next"],
            technical_understanding=parsed_json["technical_understanding"],
            reasoning=parsed_json["reasoning"],
            communication=parsed_json["communication"],
            overall_assessment=parsed_json["overall_assessment"],
        )

    except Exception as exc:
        # Gracefully handle any network, timeout, JSON parsing, or missing key error
        return _generate_fallback_feedback(plan, session, error_message=str(exc))
