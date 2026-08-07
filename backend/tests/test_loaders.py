"""
tests/test_loaders.py
---------------------
Unit tests for the candidate and curriculum data loaders.

Strategy
--------
- Real-data tests:   call the loaders against the actual JSON files shipped
                     with the project so we catch schema drift early.
- Error-path tests:  use ``tmp_path`` (pytest built-in) to create controlled
                     bad files instead of monkeypatching internals.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.loaders.candidate_loader import (
    CandidateDataMissingKeyError,
    CandidateFileInvalidJSONError,
    CandidateFileNotFoundError,
    CandidateNotFoundError,
    get_candidate,
    load_candidates,
)
from app.loaders.curriculum_loader import (
    CurriculumFileInvalidJSONError,
    CurriculumFileNotFoundError,
    load_curriculum,
)


# ══════════════════════════════════════════════════════════════════════════════
# Candidate Loader Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestLoadCandidates:
    """Tests for load_candidates()."""

    def test_loads_real_file_successfully(self) -> None:
        """Happy path: real candidates.json returns a non-empty list."""
        candidates = load_candidates()

        assert isinstance(candidates, list)
        assert len(candidates) > 0

    def test_each_record_has_required_keys(self) -> None:
        """Every candidate record must expose member, missions, and signals."""
        for entry in load_candidates():
            assert "member" in entry, f"Missing 'member' key in: {entry}"
            assert "missions" in entry, f"Missing 'missions' key in: {entry}"
            assert "signals" in entry, f"Missing 'signals' key in: {entry}"

    def test_member_has_id_field(self) -> None:
        """Each member sub-object must carry an id field."""
        for entry in load_candidates():
            assert "id" in entry["member"], f"Missing 'id' in member: {entry['member']}"

    def test_missing_file_raises_custom_exception(self, tmp_path: Path) -> None:
        """A non-existent path must raise CandidateFileNotFoundError."""
        ghost_path = tmp_path / "does_not_exist.json"

        with pytest.raises(CandidateFileNotFoundError, match="Candidates file not found"):
            load_candidates(path=ghost_path)

    def test_invalid_json_raises_custom_exception(self, tmp_path: Path) -> None:
        """Malformed JSON content must raise CandidateFileInvalidJSONError."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ this is not json }", encoding="utf-8")

        with pytest.raises(CandidateFileInvalidJSONError, match="Failed to parse"):
            load_candidates(path=bad_file)

    def test_missing_candidates_key_raises_custom_exception(self, tmp_path: Path) -> None:
        """Valid JSON without a 'candidates' key must raise CandidateDataMissingKeyError."""
        no_key_file = tmp_path / "no_key.json"
        no_key_file.write_text(json.dumps({"people": []}), encoding="utf-8")

        with pytest.raises(CandidateDataMissingKeyError, match="'candidates'"):
            load_candidates(path=no_key_file)


class TestGetCandidate:
    """Tests for get_candidate()."""

    def test_returns_correct_candidate(self) -> None:
        """get_candidate should return the record whose member.id matches."""
        # Pull the first real candidate id from the dataset dynamically.
        first = load_candidates()[0]
        first_id: str = first["member"]["id"]

        result = get_candidate(first_id)

        assert result["member"]["id"] == first_id

    def test_unknown_id_raises_not_found(self) -> None:
        """An id that does not exist in the dataset must raise CandidateNotFoundError."""
        with pytest.raises(CandidateNotFoundError, match="CAND-FAKE-999"):
            get_candidate("CAND-FAKE-999")

    def test_propagates_file_not_found(self, tmp_path: Path) -> None:
        """get_candidate propagates CandidateFileNotFoundError from load_candidates."""
        with pytest.raises(CandidateFileNotFoundError):
            get_candidate("CAND-001", path=tmp_path / "ghost.json")


# ══════════════════════════════════════════════════════════════════════════════
# Curriculum Loader Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestLoadCurriculum:
    """Tests for load_curriculum()."""

    def test_loads_real_file_successfully(self) -> None:
        """Happy path: real curriculum.json returns a non-empty dict."""
        curriculum = load_curriculum()

        assert isinstance(curriculum, dict)
        assert len(curriculum) > 0

    def test_top_level_keys_present(self) -> None:
        """Curriculum must contain the expected top-level keys."""
        curriculum = load_curriculum()

        assert "cohort" in curriculum
        assert "modules" in curriculum
        assert "days" in curriculum

    def test_modules_is_non_empty_list(self) -> None:
        """'modules' must be a non-empty list."""
        modules = load_curriculum()["modules"]

        assert isinstance(modules, list)
        assert len(modules) > 0

    def test_days_is_non_empty_list(self) -> None:
        """'days' must be a non-empty list."""
        days = load_curriculum()["days"]

        assert isinstance(days, list)
        assert len(days) > 0

    def test_missing_file_raises_custom_exception(self, tmp_path: Path) -> None:
        """A non-existent path must raise CurriculumFileNotFoundError."""
        ghost_path = tmp_path / "ghost.json"

        with pytest.raises(CurriculumFileNotFoundError, match="Curriculum file not found"):
            load_curriculum(path=ghost_path)

    def test_invalid_json_raises_custom_exception(self, tmp_path: Path) -> None:
        """Malformed JSON content must raise CurriculumFileInvalidJSONError."""
        bad_file = tmp_path / "bad_curriculum.json"
        bad_file.write_text("<<< not json >>>", encoding="utf-8")

        with pytest.raises(CurriculumFileInvalidJSONError, match="Failed to parse"):
            load_curriculum(path=bad_file)
