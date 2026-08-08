"""
candidate_profile.py (schema)
------------------------------
Pydantic schemas for validating candidate profile objects passed in requests.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class MemberProfile(BaseModel):
    """Core identity and experience information for a candidate."""

    id: str = Field(..., description="Unique candidate ID.")
    name: str = Field(..., description="Candidate display name.")
    yearsExperience: int = Field(..., description="Years of experience.")


class MissionProfile(BaseModel):
    """Details of a single curriculum mission attempted by the candidate."""

    day: int = Field(..., description="Day number of the mission.")
    title: str = Field(..., description="Title of the mission.")
    passed: Optional[bool] = Field(default=None, description="Whether the candidate passed the mission.")
    attempts: Optional[int] = Field(default=None, description="Number of attempts on the mission.")
    skipped: Optional[bool] = Field(default=None, description="Whether the mission was skipped.")


class SignalsProfile(BaseModel):
    """Aggregated performance signals for the candidate."""

    missionsCompleted: int = Field(..., description="Count of missions completed.")
    missionsFirstTry: int = Field(..., description="Count of missions passed on the first attempt.")


class CandidateProfile(BaseModel):
    """Full candidate profile schema expected in Start Interview requests."""

    member: MemberProfile = Field(..., description="Candidate member profile details.")
    missions: List[MissionProfile] = Field(..., description="Curriculum missions data.")
    signals: SignalsProfile = Field(..., description="Aggregated metric signals.")
