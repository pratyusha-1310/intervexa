"""
interview_session.py (schema)
-----------------------------
Pydantic models for the interview session state.

These models hold ONLY state — no business logic, no LLM calls.
The behavioural API lives in ``app.services.interview_session``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.interview_plan import InterviewPlan


# ── Conversation ──────────────────────────────────────────────────────────────


class ConversationEntry(BaseModel):
    """A single message in the interview conversation.

    Entries alternate between the interviewer (question) and the candidate
    (answer).  This lightweight structure is designed to be consumed later
    by the Conversation Memory component.
    """

    turn_number: int = Field(
        ..., ge=1, description="1-based sequence number within the session."
    )
    curriculum_day: int = Field(
        ..., description="The curriculum day this message relates to."
    )
    role: str = Field(
        ...,
        description="Message author: 'interviewer' or 'candidate'.",
    )
    content: str = Field(
        ..., description="The text content of the message."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this entry was recorded.",
    )


# ── Session State ─────────────────────────────────────────────────────────────


class InterviewSessionState(BaseModel):
    """Serialisable snapshot of a running interview session.

    This model is the single source of truth for interview progress.
    It can be persisted and restored without losing any state.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: str = Field(..., description="Unique session identifier (UUID4).")
    candidate_id: str = Field(..., description="Candidate's member.id from the plan.")

    # ── Plan ──────────────────────────────────────────────────────────────────
    plan: InterviewPlan = Field(
        ..., description="The frozen InterviewPlan driving this session."
    )

    # ── Position ──────────────────────────────────────────────────────────────
    current_day_index: int = Field(
        default=0,
        ge=0,
        description="0-based index into plan.selected_days for the current day.",
    )
    current_question_in_day: int = Field(
        default=0,
        ge=0,
        description="Count of questions already asked for the current day.",
    )
    total_questions_asked: int = Field(
        default=0,
        ge=0,
        description="Total questions asked across all days so far.",
    )

    # ── Progress ──────────────────────────────────────────────────────────────
    completed_days: list[int] = Field(
        default_factory=list,
        description="Curriculum day numbers that have been fully completed.",
    )

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    interview_started: bool = Field(default=False)
    interview_completed: bool = Field(default=False)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # ── Conversation ──────────────────────────────────────────────────────────
    conversation_history: list[ConversationEntry] = Field(
        default_factory=list,
        description="Ordered list of all conversation messages.",
    )
