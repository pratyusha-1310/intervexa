"""
interview_feedback.py (schema)
------------------------------
Structured Pydantic model representing interview performance evaluation.
"""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class InterviewFeedback(BaseModel):
    """
    Structured performance evaluation generated at the end of an interview session.
    """

    summary: str = Field(
        ...,
        description="A concise summary of the candidate's performance across all assessed areas.",
    )
    strengths: List[str] = Field(
        ...,
        description="Key technical strengths observed during the interview.",
    )
    gaps: List[str] = Field(
        ...,
        description="Identified areas for improvement or curriculum knowledge gaps.",
    )
    next: List[str] = Field(
        ...,
        description="Actionable next steps or recommended learning topics from the curriculum.",
    )
    technical_understanding: str = Field(
        ...,
        description="Qualitative assessment of the candidate's core technical understanding.",
    )
    reasoning: str = Field(
        ...,
        description="Qualitative assessment of the candidate's problem-solving and architectural reasoning.",
    )
    communication: str = Field(
        ...,
        description="Qualitative assessment of the candidate's technical communication skills.",
    )
    overall_assessment: str = Field(
        ...,
        description="Overall assessment and recommendation (e.g., strong pass, pass, weak pass, fail).",
    )
