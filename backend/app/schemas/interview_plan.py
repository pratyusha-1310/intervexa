"""
interview_plan.py
-----------------
Pydantic models that represent the output of the Interview Planner.

These models are INTERNAL ONLY. They are produced by
``app.services.interview_planner.build_interview_plan`` and later consumed
by the Interview Engine to conduct an adaptive technical interview.

No interview questions are stored here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ── Nested Models ──────────────────────────────────────────────────────────────


class SelectedDay(BaseModel):
    """
    A single curriculum day chosen for the interview, with full metadata
    preserved so the Interview Engine can generate targeted questions.
    """

    day: int = Field(..., description="Day number within the cohort (1–31).")
    title: str = Field(..., description="Official day title from the curriculum.")
    module_number: int = Field(..., description="Parent module number (1–8).")
    module_title: str = Field(..., description="Parent module title.")
    type: str = Field(..., description="Day type, e.g. SETUP, BUILD, MISSION, CAPSTONE.")
    tools: list[str] = Field(
        default_factory=list,
        description="Tools and technologies featured on this day.",
    )
    objectives: list[str] = Field(
        default_factory=list,
        description="Learning objectives for this day as stated in the curriculum.",
    )
    selection_reason: str = Field(
        ...,
        description="Human-readable explanation of why this day was selected.",
    )
    priority: int = Field(
        ...,
        ge=1,
        le=4,
        description=(
            "Selection priority: 1=skipped, 2=passed ≥3 attempts, "
            "3=passed in 2 attempts, 4=passed on first try."
        ),
    )
    planned_questions: int = Field(
        ...,
        ge=1,
        description="Number of questions allocated to this day in the plan.",
    )


class InterviewStatistics(BaseModel):
    """
    Lightweight summary of the generated interview plan.

    Derived entirely from the other fields of :class:`InterviewPlan`
    and intended for consumption by the Feedback Engine.
    """

    planned_questions: int = Field(
        ...,
        description="Total number of questions planned for the session.",
    )
    selected_days_count: int = Field(
        ...,
        description="Number of curriculum days selected for the interview.",
    )
    selected_modules_count: int = Field(
        ...,
        description="Number of distinct curriculum modules covered.",
    )
    selected_day_numbers: list[int] = Field(
        ...,
        description="Sorted list of selected curriculum day numbers.",
    )
    selected_module_numbers: list[int] = Field(
        ...,
        description="Sorted list of distinct module numbers covered by the selected days.",
    )


# ── Root Plan Model ────────────────────────────────────────────────────────────


class InterviewPlan(BaseModel):
    """
    Complete interview plan produced by the planner before the session starts.

    Contains ONLY planning metadata — no interview questions, no answers,
    no conversation state.
    """

    # ── Identity ───────────────────────────────────────────────────────────────
    session_id: str | None = Field(
        default=None,
        description="Optional session identifier; injected by the Interview Engine.",
    )
    candidate_id: str = Field(..., description="Candidate's member.id.")
    candidate_name: str = Field(..., description="Candidate's display name.")

    # ── Curriculum Coverage ────────────────────────────────────────────────────
    selected_days: list[SelectedDay] = Field(
        ...,
        min_length=4,
        description="Ordered list of curriculum days selected for the interview.",
    )
    selected_modules: list[str] = Field(
        ...,
        description="Deduplicated list of module titles covered by the selected days.",
    )

    # ── Question Budget ────────────────────────────────────────────────────────
    planned_question_count: int = Field(
        ...,
        ge=8,
        description="Total planned questions across all selected days (minimum 8).",
    )
    questions_per_day: dict[int, int] = Field(
        ...,
        description="Mapping of curriculum day number → planned question count.",
    )

    # ── Difficulty ─────────────────────────────────────────────────────────────
    initial_difficulty: str = Field(
        ...,
        description="Starting difficulty level: Easy | Medium | Medium-High | High.",
    )

    # ── Strategy ──────────────────────────────────────────────────────────────
    evaluation_goals: list[str] = Field(
        ...,
        description="Evaluation dimensions the interview will assess.",
    )
    interview_strategy: str = Field(
        ...,
        description="Concise internal narrative describing the overall interview approach.",
    )
    selection_reasons: dict[int, str] = Field(
        ...,
        description="Mapping of curriculum day number → human-readable selection reason.",
    )

    # ── Statistics ────────────────────────────────────────────────────────────
    interview_statistics: InterviewStatistics = Field(
        default=None,  # type: ignore[assignment]  # populated by validator below
        description="Lightweight summary of the plan for the Feedback Engine.",
    )

    # ── Audit ──────────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this plan was generated.",
    )

    @model_validator(mode="after")
    def _populate_statistics(self) -> "InterviewPlan":
        """Derive interview_statistics from the assembled plan fields.

        Runs automatically after model construction so the planner never
        has to compute these values separately.
        """
        day_numbers = sorted(d.day for d in self.selected_days)
        module_numbers = sorted(
            {d.module_number for d in self.selected_days}
        )
        self.interview_statistics = InterviewStatistics(
            planned_questions=self.planned_question_count,
            selected_days_count=len(self.selected_days),
            selected_modules_count=len(module_numbers),
            selected_day_numbers=day_numbers,
            selected_module_numbers=module_numbers,
        )
        return self

    # ── Convenience ───────────────────────────────────────────────────────────

    def day_numbers(self) -> list[int]:
        """Return the sorted list of selected day numbers."""
        return sorted(d.day for d in self.selected_days)

    def as_context_dict(self) -> dict[str, Any]:
        """
        Return a lightweight dict suitable for injecting into an LLM context.
        Strips audit fields and serialises only what the Interview Engine needs.
        """
        return {
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "initial_difficulty": self.initial_difficulty,
            "evaluation_goals": self.evaluation_goals,
            "interview_strategy": self.interview_strategy,
            "planned_question_count": self.planned_question_count,
            "selected_days": [
                {
                    "day": d.day,
                    "title": d.title,
                    "module": d.module_title,
                    "type": d.type,
                    "tools": d.tools,
                    "objectives": d.objectives,
                    "planned_questions": d.planned_questions,
                    "selection_reason": d.selection_reason,
                }
                for d in self.selected_days
            ],
            "interview_statistics": {
                "planned_questions": self.interview_statistics.planned_questions,
                "selected_days_count": self.interview_statistics.selected_days_count,
                "selected_modules_count": self.interview_statistics.selected_modules_count,
                "selected_day_numbers": self.interview_statistics.selected_day_numbers,
                "selected_module_numbers": self.interview_statistics.selected_module_numbers,
            },
        }
