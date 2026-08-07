"""
Intervexa – FastAPI Application Entry Point
============================================
Bootstraps the FastAPI app, registers middleware, and mounts all routers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.routers import core, interview

settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage startup and shutdown events.
    Place resource initialisation (connection pools, caches, etc.) in the
    startup block and teardown logic in the shutdown block.
    """
    # --- Startup ---
    print(f"[{settings.APP_NAME}] Starting up in '{settings.APP_ENV}' mode …")
    yield
    # --- Shutdown ---
    print(f"[{settings.APP_NAME}] Shutting down …")


# ── Application Factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Intervexa API – production-ready FastAPI scaffold. "
            "Extend by adding routers under `app/routers/`."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(core.router)
    app.include_router(interview.router)

    return app


app = create_app()
