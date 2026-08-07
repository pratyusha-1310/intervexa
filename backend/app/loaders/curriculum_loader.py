"""
curriculum_loader.py
--------------------
Utilities for loading the cohort curriculum dataset.

The data file is expected at:
    <project_root>/data/curriculum.json

Top-level JSON shape expected:
    {
        "cohort":   "AI Cohort · 31 days · 8 modules",
        "modules":  [ { "n": int, "title": str, "days": [int, int] }, ... ],
        "days":     [ { "day": int, "title": str, "type": str, ... }, ... ]
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ── Path resolution ────────────────────────────────────────────────────────────
_LOADERS_DIR: Path = Path(__file__).resolve().parent           # app/loaders/
_APP_DIR: Path = _LOADERS_DIR.parent                           # app/
_BACKEND_DIR: Path = _APP_DIR.parent                           # backend/
_DEFAULT_CURRICULUM_PATH: Path = _BACKEND_DIR / "data" / "curriculum.json"


# ── Custom exceptions ──────────────────────────────────────────────────────────

class CurriculumFileNotFoundError(FileNotFoundError):
    """Raised when the curriculum JSON file cannot be located on disk."""


class CurriculumFileInvalidJSONError(ValueError):
    """Raised when the curriculum file exists but contains malformed JSON."""


# ── Public API ─────────────────────────────────────────────────────────────────

def load_curriculum(
    path: Path | None = None,
) -> dict[str, Any]:
    """Load and return the full curriculum dataset.

    The returned dict mirrors the raw JSON structure::

        {
            "cohort":  str,
            "modules": [ { "n": int, "title": str, "days": [int, int] }, ... ],
            "days":    [ { "day": int, "title": str, "type": str, ... }, ... ]
        }

    Args:
        path: Optional override for the curriculum JSON file path.
              Defaults to ``<backend>/data/curriculum.json``.

    Returns:
        The parsed curriculum dict exactly as stored in the JSON file.

    Raises:
        CurriculumFileNotFoundError:   File does not exist at *path*.
        CurriculumFileInvalidJSONError: File content is not valid JSON.
    """
    file_path: Path = path or _DEFAULT_CURRICULUM_PATH

    if not file_path.exists():
        raise CurriculumFileNotFoundError(
            f"Curriculum file not found: '{file_path}'. "
            "Ensure 'data/curriculum.json' exists inside the backend directory."
        )

    try:
        raw: str = file_path.read_text(encoding="utf-8")
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CurriculumFileInvalidJSONError(
            f"Failed to parse '{file_path}' as JSON: {exc}"
        ) from exc

    return data  # type: ignore[return-value]
