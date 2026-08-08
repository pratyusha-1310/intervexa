"""
interview_decision_engine.py (service)
---------------------------------------
Deterministic decision engine for INTERVEXA.

Responsibility
~~~~~~~~~~~~~~
Evaluates current session state, interview plan, and the latest candidate answer
to decide the next action in the interview workflow:
- FOLLOW_UP
- NEXT_QUESTION
- NEXT_DAY
- END_INTERVIEW

It does NOT:
- generate interview questions
- call any LLM
- maintain session state
- produce candidate feedback

Public API
~~~~~~~~~~
- ``make_decision(plan, session, candidate_answer) -> InterviewDecision``
"""

from __future__ import annotations

from typing import Optional

from app.schemas.interview_decision import DecisionAction, InterviewDecision
from app.schemas.interview_plan import InterviewPlan
from app.services.interview_session import InterviewSession

# Minimum word count for a candidate answer to be considered complete / adequate
_MIN_ANSWER_WORD_COUNT: int = 15

# Common short / evasive phrases that trigger follow-up requests
_EVASIVE_PHRASES: set[str] = {
    "don't know",
    "dont know",
    "no idea",
    "not sure",
    "pass",
    "skip",
    "idk",
    "n/a",
    "none",
}


def _is_short_or_incomplete_answer(answer: str) -> tuple[bool, str]:
    """
    Evaluates whether a candidate's answer is too short or evasive.

    Args:
        answer: The text of the candidate's response.

    Returns:
        Tuple of (is_incomplete: bool, reason_description: str)
    """
    cleaned = answer.strip().lower()
    if not cleaned:
        return True, "Answer is empty."

    # Check for evasive phrases
    for phrase in _EVASIVE_PHRASES:
        if phrase in cleaned and len(cleaned.split()) <= 5:
            return True, f"Answer appears evasive or uninformative ('{phrase}')."

    # Check word count
    words = cleaned.split()
    if len(words) < _MIN_ANSWER_WORD_COUNT:
        return (
            True,
            f"Answer is too short ({len(words)} words; minimum {_MIN_ANSWER_WORD_COUNT} expected for full explanation).",
        )

    return False, ""


def make_decision(
    plan: InterviewPlan,
    session: InterviewSession,
    candidate_answer: Optional[str] = None,
) -> InterviewDecision:
    """
    Determines the next action for the interview based on deterministic heuristics.

    Args:
        plan: The active InterviewPlan.
        session: The running InterviewSession instance.
        candidate_answer: Optional latest text response from the candidate.

    Returns:
        An InterviewDecision object containing the recommended action and rationale.
    """
    # Rule 1: If session is already marked complete
    if session.is_complete():
        return InterviewDecision(
            action=DecisionAction.END_INTERVIEW,
            reason="Interview session is already marked complete.",
            target_day=None,
            follow_up_required=False,
            interview_complete=True,
        )

    # Rule 2: Check total planned question budget
    if session.total_questions_asked >= plan.planned_question_count:
        return InterviewDecision(
            action=DecisionAction.END_INTERVIEW,
            reason=f"Reached total planned question budget ({plan.planned_question_count} questions).",
            target_day=None,
            follow_up_required=False,
            interview_complete=True,
        )

    current_day = session.get_current_day()
    current_day_num = current_day.day

    # Rule 3: Check candidate answer for follow-up necessity (only if an answer was submitted)
    if candidate_answer is not None and candidate_answer.strip():
        # Check if we already asked a follow-up for the current question of the day.
        # We count interviewer turns for the current curriculum day in history.
        history = session.get_conversation_history()
        interviewer_turns_this_day = sum(
            1 for entry in history
            if entry.role == "interviewer" and entry.curriculum_day == current_day_num
        )
        
        # If interviewer turns on this day is greater than current_question_in_day,
        # then we have already asked a follow-up for this planned question.
        already_followed_up = interviewer_turns_this_day > session.state.current_question_in_day
        
        if not already_followed_up:
            is_incomplete, reason_desc = _is_short_or_incomplete_answer(candidate_answer)
            if is_incomplete:
                return InterviewDecision(
                    action=DecisionAction.FOLLOW_UP,
                    reason=f"Follow-up required: {reason_desc}",
                    target_day=current_day_num,
                    follow_up_required=True,
                    interview_complete=False,
                )

    # Rule 4: Check if current day's planned question quota is reached
    questions_in_day = session.state.current_question_in_day
    if questions_in_day >= current_day.planned_questions:
        # Determine if there is another day available
        current_day_idx = session.state.current_day_index
        if current_day_idx + 1 < len(plan.selected_days):
            next_day_num = plan.selected_days[current_day_idx + 1].day
            return InterviewDecision(
                action=DecisionAction.NEXT_DAY,
                reason=f"Completed planned questions ({current_day.planned_questions}) for Day {current_day_num}.",
                target_day=next_day_num,
                follow_up_required=False,
                interview_complete=False,
            )
        else:
            return InterviewDecision(
                action=DecisionAction.END_INTERVIEW,
                reason="All selected curriculum days have been completed.",
                target_day=None,
                follow_up_required=False,
                interview_complete=True,
            )

    # Rule 5: Default action — proceed to next question in the current day
    return InterviewDecision(
        action=DecisionAction.NEXT_QUESTION,
        reason=f"Proceeding to next planned question for Day {current_day_num}.",
        target_day=current_day_num,
        follow_up_required=False,
        interview_complete=False,
    )
