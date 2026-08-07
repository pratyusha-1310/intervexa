"""
interview.py (router)
---------------------
FastAPI router for the official POST /api/interview endpoint.

Keeps business logic thin by delegating orchestration to `interview_controller.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.loaders.candidate_loader import CandidateNotFoundError
from app.schemas.interview_api import InterviewApiRequest
from app.services.interview_controller import process_interview_request
from app.services.session_registry import DuplicateSessionError, SessionNotFoundError

router = APIRouter(prefix="/api", tags=["Interview"])


@router.post(
    "/interview",
    summary="Official Hackathon Interview Endpoint",
    description=(
        "Handles starting a new interview session or continuing an ongoing session "
        "with candidate message turns."
    ),
)
async def interview_endpoint(payload: InterviewApiRequest) -> JSONResponse:
    """
    Official POST /api/interview endpoint.

    Accepts:
    - Start request: {"sessionId": "...", "candidate": "..."}
    - Continue request: {"sessionId": "...", "message": "..."}

    Returns:
    - In-progress: {"reply": "...", "done": false}
    - Completed: {"reply": "...", "done": true, "feedback": null}
    """
    try:
        result_dict = process_interview_request(payload)
        return JSONResponse(content=result_dict, status_code=status.HTTP_200_OK)
    except DuplicateSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal service failure during interview processing: {exc}",
        ) from exc
