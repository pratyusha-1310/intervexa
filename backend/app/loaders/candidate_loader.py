"""
candidate_loader.py
-------------------
Utilities for loading and querying the candidate dataset.

The data file is expected at:
    <project_root>/data/candidates.json

Top-level JSON shape expected:
    {
        "candidates": [
            {
                "member": { "id": "CAND-001", ... },
                "missions": [...],
                "signals": { ... }
            },
            ...
        ]
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ── Path resolution ────────────────────────────────────────────────────────────
# Anchored to this file's location so imports work regardless of cwd.
_LOADERS_DIR: Path = Path(__file__).resolve().parent           # app/loaders/
_APP_DIR: Path = _LOADERS_DIR.parent                           # app/
_BACKEND_DIR: Path = _APP_DIR.parent                           # backend/
_DEFAULT_CANDIDATES_PATH: Path = _BACKEND_DIR / "data" / "candidates.json"


# ── Custom exceptions ──────────────────────────────────────────────────────────

class CandidateFileNotFoundError(FileNotFoundError):
    """Raised when the candidates JSON file cannot be located on disk."""


class CandidateFileInvalidJSONError(ValueError):
    """Raised when the candidates file exists but contains malformed JSON."""


class CandidateDataMissingKeyError(KeyError):
    """Raised when the parsed JSON object is missing the top-level 'candidates' key."""


class CandidateNotFoundError(LookupError):
    """Raised when a requested candidate ID does not exist in the dataset."""


# ── Public API ─────────────────────────────────────────────────────────────────

def load_candidates(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Load and return the full list of candidate records.

    Each element in the returned list is a dict with the shape::

        {
            "member":   { "id": str, "name": str, ... },
            "missions": [ { "day": int, "title": str, ... }, ... ],
            "signals":  { "commitDays": int, ... }
        }

    Args:
        path: Optional override for the candidates JSON file path.
              Defaults to ``<backend>/data/candidates.json``.

    Returns:
        A list of raw candidate dicts exactly as stored in the JSON file.

    Raises:
        CandidateFileNotFoundError:   File does not exist at *path*.
        CandidateFileInvalidJSONError: File content is not valid JSON.
        CandidateDataMissingKeyError:  Top-level ``"candidates"`` key absent.
    """
    file_path: Path = path or _DEFAULT_CANDIDATES_PATH

    if not file_path.exists():
        raise CandidateFileNotFoundError(
            f"Candidates file not found: '{file_path}'. "
            "Ensure 'data/candidates.json' exists inside the backend directory."
        )

    try:
        raw: str = file_path.read_text(encoding="utf-8")
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CandidateFileInvalidJSONError(
            f"Failed to parse '{file_path}' as JSON: {exc}"
        ) from exc

    if "candidates" not in data:
        raise CandidateDataMissingKeyError(
            f"Expected top-level key 'candidates' not found in '{file_path}'. "
            f"Found keys: {list(data.keys())}"
        )

    return data["candidates"]  # type: ignore[return-value]


def get_candidate(
    candidate_id: str,
    path: Path | None = None,
) -> dict[str, Any]:
    """Fetch a single candidate record by its member ID.

    Args:
        candidate_id: The ``member.id`` value to look up (e.g. ``"CAND-001"``).
        path:         Optional override for the candidates JSON file path.

    Returns:
        The matching candidate dict (same shape as individual elements returned
        by :func:`load_candidates`).

    Raises:
        CandidateNotFoundError:       No candidate with *candidate_id* exists.
        CandidateFileNotFoundError:   Propagated from :func:`load_candidates`.
        CandidateFileInvalidJSONError: Propagated from :func:`load_candidates`.
        CandidateDataMissingKeyError:  Propagated from :func:`load_candidates`.
    """
    candidates: list[dict[str, Any]] = load_candidates(path=path)

    for entry in candidates:
        member = entry.get("member", {})
        if member.get("id") == candidate_id:
            return entry

    raise CandidateNotFoundError(
        f"Candidate with id='{candidate_id}' was not found in the dataset."
    )
