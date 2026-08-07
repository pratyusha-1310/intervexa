"""
interview_agent.py (schema)
---------------------------
Pydantic model for the structured response returned by the AI Interview Agent.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """
    Structured output returned by the AI Interview Agent service.

    Wraps the generated interviewer message text alongside curriculum context
    and metadata for downstream consumption.
    """

    reply: str = Field(
        ...,
        description="The interviewer's conversational message text to present to the candidate.",
    )
    current_day: Optional[int] = Field(
        default=None,
        description="The curriculum day number currently being addressed.",
    )
    current_topic: Optional[str] = Field(
        default=None,
        description="The title/topic of the curriculum day currently being addressed.",
    )
    follow_up: bool = Field(
        default=False,
        description="True if this response represents a follow-up question.",
    )
