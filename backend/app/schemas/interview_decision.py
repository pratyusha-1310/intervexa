"""
interview_decision.py (schema)
------------------------------
Pydantic models and Enums for the Interview Decision Engine output.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DecisionAction(str, Enum):
    """Actions the Interview Engine can take next."""

    FOLLOW_UP = "FOLLOW_UP"
    NEXT_QUESTION = "NEXT_QUESTION"
    NEXT_DAY = "NEXT_DAY"
    END_INTERVIEW = "END_INTERVIEW"


class InterviewDecision(BaseModel):
    """
    Structured decision returned by the Decision Engine.

    Describes what action the Interview Engine should take next, along with
    explanatory metadata and context for question generation.
    """

    action: DecisionAction = Field(
        ...,
        description="The next action to execute: FOLLOW_UP, NEXT_QUESTION, NEXT_DAY, or END_INTERVIEW.",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation of why this decision was made.",
    )
    target_day: Optional[int] = Field(
        default=None,
        description="The curriculum day number for the next question/follow-up, if applicable.",
    )
    follow_up_required: bool = Field(
        default=False,
        description="True if a follow-up question is requested due to answer quality/depth.",
    )
    interview_complete: bool = Field(
        default=False,
        description="True if the interview has reached its conclusion.",
    )
