# Loaders Package
from app.loaders.candidate_loader import get_candidate, load_candidates
from app.loaders.curriculum_loader import load_curriculum

__all__ = [
    "load_candidates",
    "get_candidate",
    "load_curriculum",
]
