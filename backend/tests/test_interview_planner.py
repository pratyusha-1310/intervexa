"""
tests/test_interview_planner.py
-------------------------------
Unit and integration tests for ``app.services.interview_planner``.

Test strategy
~~~~~~~~~~~~~
- Synthetic fixtures are used for all deterministic behavioural tests so
  results are independent of the actual JSON files on disk.
- A small integration suite runs against the real data files to catch
  schema drift early and validate end-to-end wiring.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.schemas.interview_plan import InterviewPlan, SelectedDay
from app.services.interview_planner import (
    _allocate_questions,
    _build_day_index,
    _build_module_index,
    _build_selection_reason,
    _build_strategy,
    _classify_priority,
    _derive_evaluation_goals,
    _determine_difficulty,
    _select_days,
    _sort_missions,
    build_interview_plan,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures – synthetic data
# ══════════════════════════════════════════════════════════════════════════════

# A minimal curriculum covering 2 modules and 10 days.
@pytest.fixture()
def synthetic_curriculum() -> dict[str, Any]:
    return {
        "cohort": "Test Cohort · 10 days · 2 modules",
        "modules": [
            {"n": 1, "title": "Module Alpha", "days": [1, 5]},
            {"n": 2, "title": "Module Beta", "days": [6, 10]},
        ],
        "days": [
            {
                "day": d,
                "title": f"Day {d} Topic",
                "type": "BUILD",
                "tools": [f"ToolX-{d}"],
                "objectives": [f"Objective A for day {d}", f"Objective B for day {d}"],
            }
            for d in range(1, 11)
        ],
    }


def _make_candidate(
    cand_id: str = "TEST-001",
    name: str = "Test User",
    job_role: str = "Software Engineer",
    years: int = 3,
    missions: list[dict[str, Any]] | None = None,
    commit_days: int = 10,
    completed: int = 10,
    first_try: int = 5,
) -> dict[str, Any]:
    """Factory for synthetic candidate records."""
    if missions is None:
        missions = [
            {"day": 1, "title": "Day 1 Topic", "passed": True, "attempts": 1},
            {"day": 2, "title": "Day 2 Topic", "passed": True, "attempts": 2},
            {"day": 3, "title": "Day 3 Topic", "passed": True, "attempts": 3},
            {"day": 4, "title": "Day 4 Topic", "passed": True, "attempts": 4},
            {"day": 5, "title": "Day 5 Topic", "skipped": True},
        ]
    return {
        "member": {
            "id": cand_id,
            "name": name,
            "jobRole": job_role,
            "yearsExperience": years,
            "education": "B.Sc CS",
            "status": "COMPLETED",
        },
        "missions": missions,
        "signals": {
            "commitDays": commit_days,
            "missionsCompleted": completed,
            "missionsFirstTry": first_try,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# _classify_priority
# ══════════════════════════════════════════════════════════════════════════════


class TestClassifyPriority:
    def test_skipped_is_priority_1(self) -> None:
        assert _classify_priority({"day": 5, "skipped": True}) == 1

    def test_three_or_more_attempts_is_priority_2(self) -> None:
        assert _classify_priority({"day": 3, "passed": True, "attempts": 3}) == 2
        assert _classify_priority({"day": 3, "passed": True, "attempts": 5}) == 2

    def test_two_attempts_is_priority_3(self) -> None:
        assert _classify_priority({"day": 2, "passed": True, "attempts": 2}) == 3

    def test_one_attempt_is_priority_4(self) -> None:
        assert _classify_priority({"day": 1, "passed": True, "attempts": 1}) == 4

    def test_missing_attempts_defaults_to_priority_4(self) -> None:
        assert _classify_priority({"day": 1, "passed": True}) == 4


# ══════════════════════════════════════════════════════════════════════════════
# _sort_missions
# ══════════════════════════════════════════════════════════════════════════════


class TestSortMissions:
    def test_skipped_missions_come_first(self) -> None:
        missions = [
            {"day": 1, "passed": True, "attempts": 1},
            {"day": 2, "skipped": True},
            {"day": 3, "passed": True, "attempts": 4},
        ]
        sorted_missions = _sort_missions(missions)
        priorities = [p for p, _ in sorted_missions]
        # Priority 1 (skipped) must be first.
        assert priorities[0] == 1

    def test_higher_attempt_missions_precede_first_pass_within_same_band(self) -> None:
        missions = [
            {"day": 10, "passed": True, "attempts": 1},
            {"day": 11, "passed": True, "attempts": 5},
            {"day": 12, "passed": True, "attempts": 3},
        ]
        sorted_missions = _sort_missions(missions)
        # All are priority 2 or 4; the highest-attempt priority-2 items come before priority-4.
        priorities = [p for p, _ in sorted_missions]
        attempt_order = [m.get("attempts", 0) for _, m in sorted_missions]
        # The first entry must have priority 2 (attempts ≥ 3).
        assert priorities[0] == 2
        # Within priority-2 band, higher attempts come first.
        p2_missions = [(p, m) for p, m in sorted_missions if p == 2]
        p2_attempts = [m["attempts"] for _, m in p2_missions]
        assert p2_attempts == sorted(p2_attempts, reverse=True)

    def test_priority_4_last(self) -> None:
        missions = [
            {"day": 1, "passed": True, "attempts": 1},
            {"day": 2, "passed": True, "attempts": 3},
            {"day": 3, "skipped": True},
        ]
        sorted_missions = _sort_missions(missions)
        priorities = [p for p, _ in sorted_missions]
        assert priorities[-1] == 4


# ══════════════════════════════════════════════════════════════════════════════
# _determine_difficulty
# ══════════════════════════════════════════════════════════════════════════════


class TestDetermineDifficulty:
    def _signals(self, completed: int = 10, first_try: int = 8) -> dict[str, Any]:
        return {"missionsCompleted": completed, "missionsFirstTry": first_try}

    def test_junior_experience_maps_to_easy(self) -> None:
        member = {"yearsExperience": 1}
        assert _determine_difficulty(member, self._signals()) == "Easy"

    def test_mid_experience_maps_to_medium(self) -> None:
        member = {"yearsExperience": 3}
        assert _determine_difficulty(member, self._signals()) == "Medium"

    def test_senior_experience_maps_to_medium_high(self) -> None:
        member = {"yearsExperience": 6}
        assert _determine_difficulty(member, self._signals()) == "Medium-High"

    def test_very_experienced_maps_to_high(self) -> None:
        member = {"yearsExperience": 9}
        assert _determine_difficulty(member, self._signals()) == "High"

    def test_low_first_try_ratio_caps_high_at_medium_high(self) -> None:
        """A very experienced candidate with < 40 % first-try ratio is capped at Medium-High."""
        member = {"yearsExperience": 10}
        low_ratio_signals = {"missionsCompleted": 30, "missionsFirstTry": 5}
        assert _determine_difficulty(member, low_ratio_signals) == "Medium-High"

    def test_zero_experience_defaults_to_easy(self) -> None:
        member = {"yearsExperience": 0}
        assert _determine_difficulty(member, self._signals()) == "Easy"


# ══════════════════════════════════════════════════════════════════════════════
# _select_days
# ══════════════════════════════════════════════════════════════════════════════


class TestSelectDays:
    def test_selects_minimum_four_days(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        day_index = _build_day_index(synthetic_curriculum)
        module_index = _build_module_index(synthetic_curriculum)
        candidate = _make_candidate()
        sorted_missions = _sort_missions(candidate["missions"])
        selection = _select_days(sorted_missions, day_index, module_index)
        assert len(selection) >= 4

    def test_skipped_day_is_selected_first(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        missions = [
            {"day": 1, "passed": True, "attempts": 1},
            {"day": 2, "passed": True, "attempts": 1},
            {"day": 3, "passed": True, "attempts": 1},
            {"day": 4, "passed": True, "attempts": 1},
            {"day": 5, "skipped": True},
        ]
        candidate = _make_candidate(missions=missions)
        day_index = _build_day_index(synthetic_curriculum)
        module_index = _build_module_index(synthetic_curriculum)
        sorted_missions = _sort_missions(candidate["missions"])
        selection = _select_days(sorted_missions, day_index, module_index)
        first_priority = selection[0][0]
        assert first_priority == 1, "Skipped day must be selected first (priority 1)."

    def test_days_absent_from_curriculum_are_skipped(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        missions = [
            {"day": 99, "passed": True, "attempts": 1},  # Not in curriculum
            {"day": 1, "passed": True, "attempts": 1},
            {"day": 2, "passed": True, "attempts": 1},
            {"day": 3, "passed": True, "attempts": 1},
            {"day": 4, "passed": True, "attempts": 1},
        ]
        candidate = _make_candidate(missions=missions)
        day_index = _build_day_index(synthetic_curriculum)
        module_index = _build_module_index(synthetic_curriculum)
        sorted_missions = _sort_missions(candidate["missions"])
        selection = _select_days(sorted_missions, day_index, module_index)
        selected_days = [curriculum_day["day"] for _, _, curriculum_day, _ in selection]
        assert 99 not in selected_days


# ══════════════════════════════════════════════════════════════════════════════
# _allocate_questions
# ══════════════════════════════════════════════════════════════════════════════


class TestAllocateQuestions:
    def _make_selection(
        self, day_priorities: list[tuple[int, int]]
    ) -> list[tuple[int, dict, dict, dict]]:
        """Build a minimal selection fixture: (day, priority) → 4-tuple."""
        result = []
        for day_num, priority in day_priorities:
            mission = {"day": day_num, "passed": True, "attempts": 1}
            curriculum_day = {"day": day_num, "title": f"Day {day_num}"}
            module = {"n": 1, "title": "M1"}
            result.append((priority, mission, curriculum_day, module))
        return result

    def test_total_meets_minimum(self) -> None:
        selection = self._make_selection([(1, 4), (2, 4), (3, 4), (4, 4)])
        alloc = _allocate_questions(selection)
        assert sum(alloc.values()) >= 8

    def test_top_up_applied_when_base_is_low(self) -> None:
        """Four first-try days give base total of 4 — must be topped up to 8."""
        selection = self._make_selection([(1, 4), (2, 4), (3, 4), (4, 4)])
        alloc = _allocate_questions(selection)
        assert sum(alloc.values()) == 8

    def test_skipped_day_gets_more_questions_than_first_try(self) -> None:
        selection = self._make_selection([(10, 1), (20, 4)])
        alloc = _allocate_questions(selection)
        assert alloc[10] >= alloc[20]


# ══════════════════════════════════════════════════════════════════════════════
# build_interview_plan – end-to-end (synthetic)
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildInterviewPlan:
    def test_returns_interview_plan_instance(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        assert isinstance(plan, InterviewPlan)

    def test_minimum_eight_questions(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        assert plan.planned_question_count >= 8

    def test_minimum_four_curriculum_days(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        assert len(plan.selected_days) >= 4

    def test_candidate_id_and_name_set_correctly(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate(cand_id="CAND-XYZ", name="Jane Doe")
        plan = build_interview_plan(candidate, synthetic_curriculum)
        assert plan.candidate_id == "CAND-XYZ"
        assert plan.candidate_name == "Jane Doe"

    def test_skipped_missions_are_highest_priority(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        """The selected day with priority 1 (skipped) must appear before priority 4 days."""
        missions = [
            {"day": 1, "passed": True, "attempts": 1},
            {"day": 2, "passed": True, "attempts": 1},
            {"day": 3, "passed": True, "attempts": 1},
            {"day": 4, "passed": True, "attempts": 1},
            {"day": 5, "skipped": True},
        ]
        candidate = _make_candidate(missions=missions)
        plan = build_interview_plan(candidate, synthetic_curriculum)

        priorities = [d.priority for d in plan.selected_days]
        # Priority 1 must appear somewhere in the plan.
        assert 1 in priorities, "Skipped day (priority 1) must be present in the plan."

    def test_higher_attempt_missions_prioritised_over_first_pass(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        """A day with 5 attempts must have higher or equal priority than a day with 1 attempt."""
        missions = [
            {"day": 1, "passed": True, "attempts": 1},
            {"day": 2, "passed": True, "attempts": 5},
            {"day": 3, "passed": True, "attempts": 1},
            {"day": 4, "passed": True, "attempts": 1},
            {"day": 5, "passed": True, "attempts": 1},
        ]
        candidate = _make_candidate(missions=missions)
        plan = build_interview_plan(candidate, synthetic_curriculum)

        day_priorities = {d.day: d.priority for d in plan.selected_days}
        if 2 in day_priorities and 1 in day_priorities:
            assert day_priorities[2] <= day_priorities[1], (
                "Day 2 (5 attempts) must have priority ≤ day 1 (1 attempt)."
            )

    def test_difficulty_assigned_based_on_experience(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        junior = _make_candidate(years=1)
        senior = _make_candidate(years=9, first_try=9)

        junior_plan = build_interview_plan(junior, synthetic_curriculum)
        senior_plan = build_interview_plan(senior, synthetic_curriculum)

        assert junior_plan.initial_difficulty == "Easy"
        assert senior_plan.initial_difficulty == "High"

    def test_curriculum_metadata_preserved_in_selected_days(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        """Every SelectedDay must carry non-empty tools and objectives from the curriculum."""
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)

        for day in plan.selected_days:
            assert isinstance(day, SelectedDay)
            assert day.title != ""
            assert day.module_title != ""
            assert day.type != ""
            assert len(day.tools) > 0, f"Day {day.day} is missing tools."
            assert len(day.objectives) > 0, f"Day {day.day} is missing objectives."

    def test_questions_per_day_matches_selected_days(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)

        selected_day_nums = {d.day for d in plan.selected_days}
        assert set(plan.questions_per_day.keys()) == selected_day_nums

    def test_questions_per_day_sums_to_planned_count(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        assert sum(plan.questions_per_day.values()) == plan.planned_question_count

    def test_selection_reasons_cover_all_selected_days(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        selected_day_nums = {d.day for d in plan.selected_days}
        assert set(plan.selection_reasons.keys()) == selected_day_nums

    def test_evaluation_goals_non_empty(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        assert len(plan.evaluation_goals) > 0

    def test_interview_strategy_non_empty(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        assert isinstance(plan.interview_strategy, str)
        assert len(plan.interview_strategy) > 10

    def test_plan_contains_no_questions(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        """Ensure the plan model carries no generated question content."""
        candidate = _make_candidate()
        plan = build_interview_plan(candidate, synthetic_curriculum)
        plan_dict = plan.model_dump()
        assert "questions" not in plan_dict
        assert "generated_questions" not in plan_dict
        assert "question_text" not in plan_dict


# ══════════════════════════════════════════════════════════════════════════════
# Integration – real JSON files
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildInterviewPlanIntegration:
    """Run the planner against the real data files to catch schema drift."""

    @pytest.fixture(autouse=True)
    def _load_real_data(self) -> None:
        from app.loaders.candidate_loader import load_candidates
        from app.loaders.curriculum_loader import load_curriculum

        self.all_candidates = load_candidates()
        self.curriculum = load_curriculum()

    def test_plan_succeeds_for_all_real_candidates(self) -> None:
        for candidate in self.all_candidates:
            plan = build_interview_plan(candidate, self.curriculum)
            assert isinstance(plan, InterviewPlan)
            assert plan.planned_question_count >= 8
            assert len(plan.selected_days) >= 4

    def test_real_candidate_cand_001(self) -> None:
        """CAND-001 has 1 skipped day (day 29) — it must be priority 1 in the plan."""
        candidate = next(
            c for c in self.all_candidates if c["member"]["id"] == "CAND-001"
        )
        plan = build_interview_plan(candidate, self.curriculum)

        skipped_days = [d for d in plan.selected_days if d.priority == 1]
        assert len(skipped_days) >= 1
        assert any(d.day == 29 for d in skipped_days)

    def test_real_plan_preserves_curriculum_objectives(self) -> None:
        candidate = self.all_candidates[0]
        plan = build_interview_plan(candidate, self.curriculum)
        for day in plan.selected_days:
            assert len(day.objectives) > 0, (
                f"Day {day.day} is missing objectives in the real curriculum."
            )


# ══════════════════════════════════════════════════════════════════════════════
# B3.1 – InterviewStatistics
# ══════════════════════════════════════════════════════════════════════════════


class TestInterviewStatistics:
    """Verify the interview_statistics field is populated and correct."""

    def test_statistics_field_exists(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        plan = build_interview_plan(_make_candidate(), synthetic_curriculum)
        assert hasattr(plan, "interview_statistics")
        assert plan.interview_statistics is not None

    def test_planned_questions_matches_plan(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        plan = build_interview_plan(_make_candidate(), synthetic_curriculum)
        assert plan.interview_statistics.planned_questions == plan.planned_question_count

    def test_selected_days_count_is_correct(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        plan = build_interview_plan(_make_candidate(), synthetic_curriculum)
        assert plan.interview_statistics.selected_days_count == len(plan.selected_days)

    def test_selected_modules_count_is_correct(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        plan = build_interview_plan(_make_candidate(), synthetic_curriculum)
        expected = len({d.module_number for d in plan.selected_days})
        assert plan.interview_statistics.selected_modules_count == expected

    def test_selected_day_numbers_are_correct_and_sorted(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        plan = build_interview_plan(_make_candidate(), synthetic_curriculum)
        expected = sorted(d.day for d in plan.selected_days)
        assert plan.interview_statistics.selected_day_numbers == expected

    def test_selected_module_numbers_are_correct_and_sorted(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        plan = build_interview_plan(_make_candidate(), synthetic_curriculum)
        expected = sorted({d.module_number for d in plan.selected_days})
        assert plan.interview_statistics.selected_module_numbers == expected

    def test_statistics_included_in_context_dict(
        self, synthetic_curriculum: dict[str, Any]
    ) -> None:
        plan = build_interview_plan(_make_candidate(), synthetic_curriculum)
        ctx = plan.as_context_dict()
        assert "interview_statistics" in ctx
        stats = ctx["interview_statistics"]
        assert stats["planned_questions"] == plan.planned_question_count
        assert stats["selected_days_count"] == len(plan.selected_days)
        assert stats["selected_modules_count"] == plan.interview_statistics.selected_modules_count
        assert isinstance(stats["selected_day_numbers"], list)
        assert isinstance(stats["selected_module_numbers"], list)
