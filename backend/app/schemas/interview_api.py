"""
interview_api.py (schema)
-------------------------
Pydantic schemas for the official POST /api/interview endpoint.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class InterviewApiRequest(BaseModel):
    """
    Request payload for POST /api/interview.

    Supports two modes:
    1. Start Interview: sessionId + candidate
    2. Continue Interview: sessionId + message
    """

    session_id: Optional[str] = Field(
        default=None,
        alias="sessionId",
        description="Unique session identifier string.",
    )
    candidate: Optional[Any] = Field(
        default=None,
        description="Candidate ID string or candidate object containing ID.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Candidate's conversational response message.",
    )

    model_config = ConfigDict(
        populate_by_name=True,
    )


class InterviewApiResponse(BaseModel):
    """
    Response payload for POST /api/interview.

    - During interview: {"reply": "...", "done": false}
    - When completed: {"reply": "...", "done": true, "feedback": null}
    """

    reply: str = Field(..., description="The interviewer's response message.")
    done: bool = Field(..., description="True if the interview has concluded.")
    feedback: Optional[Any] = Field(
        default=None,
        description="Structured feedback object (null until Feedback Engine milestone B6).",
    )

    model_config = ConfigDict(
        populate_by_name=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializes response according to official API spec."""
        if not self.done:
            return {"reply": self.reply, "done": False}
        return {"reply": self.reply, "done": True, "feedback": None}
