"""
interview_planner.py
--------------------
Deterministic interview planner for INTERVEXA.

Responsibility
~~~~~~~~~~~~~~
Given a candidate record (from ``candidate_loader``) and the full curriculum
(from ``curriculum_loader``), produce an :class:`~app.schemas.interview_plan.InterviewPlan`
that describes WHAT the interview will cover and HOW it will be structured.

This module does NOT:
- generate interview questions
- call any LLM
- maintain conversation state
- produce candidate feedback
- expose any HTTP endpoint

The resulting ``InterviewPlan`` is consumed later by the Interview Engine.

Public API
~~~~~~~~~~
``build_interview_plan(candidate, curriculum)  →  InterviewPlan``
"""

from __future__ import annotations

from typing import Any

from app.schemas.interview_plan import InterviewPlan, SelectedDay

# ── Constants ──────────────────────────────────────────────────────────────────

_MIN_QUESTIONS: int = 8
_MIN_DAYS: int = 4

# Base question allocation per selection priority.
# Priority 1 (skipped) earns the most scrutiny; priority 4 (first-try) the least.
_PRIORITY_QUESTION_BASE: dict[int, int] = {1: 3, 2: 2, 3: 2, 4: 1}

# Difficulty bands keyed by years of experience.
# Used as the primary axis; signals may bump the band (see _determine_difficulty).
_EXPERIENCE_DIFFICULTY: list[tuple[int, str]] = [
    (2,  "Easy"),         # < 2 yrs  → Junior
    (5,  "Medium"),       # 2–4 yrs  → Mid-level
    (8,  "Medium-High"),  # 5–7 yrs  → Senior
    (999, "High"),        # 8+ yrs   → Very experienced
]

# Possible evaluation goals and when they are included.
_UNIVERSAL_GOALS: list[str] = ["Technical Understanding", "Communication"]
_SENIOR_GOALS: list[str] = [
    "Architecture Thinking",
    "Trade-off Analysis",
    "Production Readiness",
]
_MID_GOALS: list[str] = ["Problem Solving", "Trade-off Analysis"]
_JUNIOR_GOALS: list[str] = ["Problem Solving"]
_STRUGGLE_GOAL: str = "Debugging Ability"


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers – curriculum indexing
# ══════════════════════════════════════════════════════════════════════════════


def _build_day_index(curriculum: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Return a mapping of ``day_number → curriculum day object``.

    Args:
        curriculum: Full curriculum dict from ``load_curriculum()``.

    Returns:
        Dict keyed by integer day number.
    """
    return {entry["day"]: entry for entry in curriculum.get("days", [])}


def _build_module_index(curriculum: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Return a mapping of ``day_number → parent module object``.

    Each module defines an inclusive ``[start, end]`` day range.

    Args:
        curriculum: Full curriculum dict from ``load_curriculum()``.

    Returns:
        Dict keyed by integer day number, values are module dicts.
    """
    index: dict[int, dict[str, Any]] = {}
    for module in curriculum.get("modules", []):
        start, end = module["days"]
        for day_num in range(start, end + 1):
            index[day_num] = module
    return index


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers – mission prioritisation
# ══════════════════════════════════════════════════════════════════════════════


def _classify_priority(mission: dict[str, Any]) -> int:
    """Assign a selection priority to a candidate mission.

    Lower number = higher importance for the interview.

    Priority rules
    ~~~~~~~~~~~~~~
    1 — Mission was skipped entirely.
    2 — Mission passed, but required ≥ 3 attempts.
    3 — Mission passed in exactly 2 attempts.
    4 — Mission passed on the first attempt.

    Args:
        mission: A single mission dict from the candidate's missions list.

    Returns:
        Integer priority in the range [1, 4].
    """
    if mission.get("skipped"):
        return 1

    attempts: int = mission.get("attempts", 1)
    if attempts >= 3:
        return 2
    if attempts == 2:
        return 3
    return 4


def _build_selection_reason(priority: int, attempts: int) -> str:
    """Produce a concise, human-readable reason for day selection.

    Args:
        priority: The priority assigned by :func:`_classify_priority`.
        attempts: Number of attempts recorded for the mission (0 if skipped).

    Returns:
        A short explanatory string.
    """
    if priority == 1:
        return "Skipped during cohort — foundational gap to be probed."
    if priority == 2:
        return f"Passed after {attempts} attempts — signals difficulty with this topic."
    if priority == 3:
        return "Required two attempts — worth revisiting for deeper understanding."
    return "Passed on the first attempt — included for breadth coverage."


def _sort_missions(missions: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """Sort candidate missions by priority, then by descending attempt count.

    Returns a list of ``(priority, mission)`` tuples, highest-priority first.

    The secondary sort by attempts (descending) ensures that within the same
    priority band, the hardest missions surface first.

    Args:
        missions: Raw mission list from the candidate record.

    Returns:
        Sorted list of ``(priority, mission)`` tuples.
    """
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for mission in missions:
        priority = _classify_priority(mission)
        attempts = mission.get("attempts", 0)
        scored.append((priority, attempts, mission))

    # Sort ascending by priority, then descending by attempts within the band.
    scored.sort(key=lambda t: (t[0], -t[1]))
    return [(p, m) for p, _, m in scored]


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers – day selection
# ══════════════════════════════════════════════════════════════════════════════


def _select_days(
    sorted_missions: list[tuple[int, dict[str, Any]]],
    day_index: dict[int, dict[str, Any]],
    module_index: dict[int, dict[str, Any]],
) -> list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Select curriculum days from the candidate's sorted mission list.

    Only missions that have a matching day in the official curriculum are
    eligible. Days that appear in the candidate's missions but are absent
    from the curriculum are silently skipped (defensive against schema drift).

    Selects enough days to satisfy ``_MIN_DAYS`` and ``_MIN_QUESTIONS``.

    Args:
        sorted_missions: Output of :func:`_sort_missions`.
        day_index:       Output of :func:`_build_day_index`.
        module_index:    Output of :func:`_build_module_index`.

    Returns:
        List of ``(priority, mission, curriculum_day, module)`` 4-tuples,
        in selection order (highest priority first).
    """
    selected: list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    total_questions = 0

    for priority, mission in sorted_missions:
        day_num: int = mission["day"]

        curriculum_day = day_index.get(day_num)
        module = module_index.get(day_num)

        # Skip days absent from the curriculum (defensive).
        if curriculum_day is None or module is None:
            continue

        base_q = _PRIORITY_QUESTION_BASE[priority]
        selected.append((priority, mission, curriculum_day, module))
        total_questions += base_q

        # Stop once both minimum constraints are satisfied.
        if len(selected) >= _MIN_DAYS and total_questions >= _MIN_QUESTIONS:
            break

    return selected


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers – question budget
# ══════════════════════════════════════════════════════════════════════════════


def _allocate_questions(
    selection: list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]],
) -> dict[int, int]:
    """Compute a per-day question allocation that meets the minimum total.

    Base allocation uses ``_PRIORITY_QUESTION_BASE``. If the sum is still
    below ``_MIN_QUESTIONS`` after all selected days are counted, extra
    questions are distributed starting from the highest-priority days.

    Args:
        selection: Output of :func:`_select_days`.

    Returns:
        Dict mapping ``day_number → planned_question_count``.
    """
    allocation: dict[int, int] = {}
    for priority, mission, curriculum_day, _module in selection:
        day_num: int = curriculum_day["day"]
        allocation[day_num] = _PRIORITY_QUESTION_BASE[priority]

    # Top up until we hit the minimum.
    shortfall = _MIN_QUESTIONS - sum(allocation.values())
    if shortfall > 0:
        # Distribute one extra question per round to the highest-priority days.
        priority_order = [curriculum_day["day"] for _, _, curriculum_day, _ in selection]
        idx = 0
        while shortfall > 0:
            day_num = priority_order[idx % len(priority_order)]
            allocation[day_num] += 1
            shortfall -= 1
            idx += 1

    return allocation


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers – difficulty
# ══════════════════════════════════════════════════════════════════════════════


def _determine_difficulty(
    member: dict[str, Any],
    signals: dict[str, Any],
) -> str:
    """Map candidate profile to an initial interview difficulty.

    Primary axis: ``yearsExperience``.
    Secondary adjustment: if the first-try ratio is low (< 40 %), the
    candidate may be overestimating their level — difficulty is kept or
    lowered by one band, never raised.

    Bands
    ~~~~~
    - Easy        → Junior      (< 2 yrs experience)
    - Medium      → Mid-level   (2–4 yrs)
    - Medium-High → Senior      (5–7 yrs)
    - High        → Very exp.   (≥ 8 yrs)

    Args:
        member:  The ``member`` sub-object from the candidate record.
        signals: The ``signals`` sub-object from the candidate record.

    Returns:
        Difficulty string: ``"Easy"``, ``"Medium"``, ``"Medium-High"``, or ``"High"``.
    """
    years: int = member.get("yearsExperience", 0)

    # Determine base band from experience.
    difficulty = "Easy"
    for threshold, band in _EXPERIENCE_DIFFICULTY:
        if years < threshold:
            difficulty = band
            break

    # Secondary signal: first-try ratio.
    completed: int = signals.get("missionsCompleted", 1) or 1
    first_try: int = signals.get("missionsFirstTry", 0)
    first_try_ratio: float = first_try / completed

    # If the candidate struggled significantly (< 40 % first-try), cap at Medium-High.
    _BAND_ORDER = ["Easy", "Medium", "Medium-High", "High"]
    if first_try_ratio < 0.40 and difficulty == "High":
        difficulty = "Medium-High"

    return difficulty


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers – evaluation goals
# ══════════════════════════════════════════════════════════════════════════════


def _derive_evaluation_goals(
    signals: dict[str, Any],
    difficulty: str,
) -> list[str]:
    """Choose the most relevant evaluation goals for this candidate.

    Selection rules (applied in order):

    - All candidates receive the universal goals.
    - Difficulty-specific goals are added.
    - If the first-try ratio is below 50 %, Debugging Ability is appended.

    Args:
        signals:    The ``signals`` sub-object from the candidate record.
        difficulty: Output of :func:`_determine_difficulty`.

    Returns:
        Ordered, deduplicated list of evaluation goal strings.
    """
    goals: list[str] = list(_UNIVERSAL_GOALS)

    if difficulty in ("High", "Medium-High"):
        goals.extend(_SENIOR_GOALS)
    elif difficulty == "Medium":
        goals.extend(_MID_GOALS)
    else:
        goals.extend(_JUNIOR_GOALS)

    completed: int = signals.get("missionsCompleted", 1) or 1
    first_try: int = signals.get("missionsFirstTry", 0)
    if (first_try / completed) < 0.50:
        goals.append(_STRUGGLE_GOAL)

    # Deduplicate while preserving insertion order.
    seen: set[str] = set()
    unique_goals: list[str] = []
    for goal in goals:
        if goal not in seen:
            seen.add(goal)
            unique_goals.append(goal)

    return unique_goals


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers – interview strategy narrative
# ══════════════════════════════════════════════════════════════════════════════


def _build_strategy(
    selection: list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]],
    difficulty: str,
) -> str:
    """Generate a deterministic, concise interview strategy narrative.

    The narrative is composed from clauses selected by analysing the
    priority distribution of the chosen days and the difficulty level.

    Args:
        selection:  Output of :func:`_select_days`.
        difficulty: Output of :func:`_determine_difficulty`.

    Returns:
        A single-paragraph strategy string for internal use.
    """
    priorities = [p for p, *_ in selection]
    has_skipped = 1 in priorities
    has_struggled = 2 in priorities
    has_retry = 3 in priorities
    is_senior = difficulty in ("High", "Medium-High")

    opening_clauses: list[str] = []
    closing_clauses: list[str] = []

    if has_skipped:
        opening_clauses.append(
            "open by probing entirely skipped curriculum areas to surface foundational gaps"
        )
    if has_struggled:
        opening_clauses.append(
            "stress-test topics where the candidate required multiple attempts"
        )
    if has_retry and not has_struggled:
        opening_clauses.append(
            "revisit topics that required a second pass to check for durable understanding"
        )

    if is_senior:
        closing_clauses.append(
            "escalate progressively to architecture design, trade-off analysis, "
            "and production-readiness discussions"
        )
    else:
        closing_clauses.append(
            "close with structured problem-solving scenarios to gauge learning trajectory"
        )

    all_clauses = opening_clauses + closing_clauses
    if not all_clauses:
        return (
            "Cover selected curriculum topics in priority order, "
            "adapting depth based on candidate responses."
        )

    return "Begin by " + "; then ".join(all_clauses) + "."


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


def build_interview_plan(
    candidate: dict[str, Any],
    curriculum: dict[str, Any],
) -> InterviewPlan:
    """Build a complete, deterministic interview plan for the given candidate.

    This is the single public entry point of this module. It orchestrates
    all private helpers and returns a validated :class:`InterviewPlan`.

    No LLMs are called. No questions are generated. This function is
    purely a planning step.

    Args:
        candidate:  A single candidate record as returned by
                    ``candidate_loader.get_candidate()`` or
                    ``candidate_loader.load_candidates()[n]``.
                    Must contain ``member``, ``missions``, and ``signals``.

        curriculum: The full curriculum dict as returned by
                    ``curriculum_loader.load_curriculum()``.
                    Must contain ``modules`` and ``days``.

    Returns:
        A fully populated and validated :class:`~app.schemas.interview_plan.InterviewPlan`.

    Raises:
        ValueError: If fewer than ``_MIN_DAYS`` eligible days can be found
                    in the intersection of the candidate's missions and the
                    official curriculum.
    """
    member: dict[str, Any] = candidate["member"]
    missions: list[dict[str, Any]] = candidate["missions"]
    signals: dict[str, Any] = candidate["signals"]

    # ── 1. Index curriculum ────────────────────────────────────────────────────
    day_index = _build_day_index(curriculum)
    module_index = _build_module_index(curriculum)

    # ── 2. Sort missions by priority ───────────────────────────────────────────
    sorted_missions = _sort_missions(missions)

    # ── 3. Select days ────────────────────────────────────────────────────────
    selection = _select_days(sorted_missions, day_index, module_index)

    if len(selection) < _MIN_DAYS:
        raise ValueError(
            f"Could not select the required minimum of {_MIN_DAYS} curriculum days "
            f"for candidate '{member['id']}'. "
            f"Only {len(selection)} eligible day(s) found in the curriculum."
        )

    # ── 4. Allocate questions ──────────────────────────────────────────────────
    questions_per_day = _allocate_questions(selection)

    # ── 5. Difficulty & goals ─────────────────────────────────────────────────
    difficulty = _determine_difficulty(member, signals)
    evaluation_goals = _derive_evaluation_goals(signals, difficulty)

    # ── 6. Strategy narrative ──────────────────────────────────────────────────
    strategy = _build_strategy(selection, difficulty)

    # ── 7. Assemble SelectedDay objects ───────────────────────────────────────
    selected_days: list[SelectedDay] = []
    selection_reasons: dict[int, str] = {}

    for priority, mission, curriculum_day, module in selection:
        day_num: int = curriculum_day["day"]
        attempts: int = mission.get("attempts", 0)
        reason = _build_selection_reason(priority, attempts)
        selection_reasons[day_num] = reason

        selected_days.append(
            SelectedDay(
                day=day_num,
                title=curriculum_day["title"],
                module_number=module["n"],
                module_title=module["title"],
                type=curriculum_day.get("type", ""),
                tools=curriculum_day.get("tools", []),
                objectives=curriculum_day.get("objectives", []),
                selection_reason=reason,
                priority=priority,
                planned_questions=questions_per_day[day_num],
            )
        )

    # Sort selected days by day number for a logical interview flow.
    selected_days.sort(key=lambda d: d.day)

    # ── 8. Collect unique module titles ───────────────────────────────────────
    seen_modules: set[int] = set()
    selected_modules: list[str] = []
    for day in sorted(selected_days, key=lambda d: d.module_number):
        if day.module_number not in seen_modules:
            seen_modules.add(day.module_number)
            selected_modules.append(day.module_title)

    # ── 9. Build and return the plan ──────────────────────────────────────────
    return InterviewPlan(
        candidate_id=member["id"],
        candidate_name=member["name"],
        selected_days=selected_days,
        selected_modules=selected_modules,
        planned_question_count=sum(questions_per_day.values()),
        questions_per_day=questions_per_day,
        initial_difficulty=difficulty,
        evaluation_goals=evaluation_goals,
        interview_strategy=strategy,
        selection_reasons=selection_reasons,
    )
