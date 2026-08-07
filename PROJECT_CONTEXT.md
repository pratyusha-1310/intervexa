# PROJECT_CONTEXT.md

# Intervexa – Project Context

## Project Overview

Intervexa is an AI-powered adaptive interview agent built for a prompt-only hackathon.

The system evaluates candidates by conducting structured, context-aware interviews using:
- Curriculum JSON
- Candidate Profile
- Conversation Memory
- AI-generated follow-up questions
- Structured feedback generation

The primary goal is to build a polished, demo-ready backend within 24 hours.

---

## Current Architecture

Curriculum JSON
        +
Candidate Profile
        │
        ▼
Interview Planner
        │
        ▼
Interview Agent
        │
        ▼
Conversation Memory
        │
        ▼
Feedback Generator

---

## Backend Stack

- Python 3.12+
- FastAPI
- Pydantic v2
- Uvicorn
- Pydantic Settings

---

## Current Status

### Completed

- Project initialization
- Repository setup
- Backend scaffold
- Root endpoint
- Health endpoint
- Swagger/OpenAPI
- Basic project structure
- Initial tests

### Pending

- API routing
- Candidate Loader
- Curriculum Loader
- Interview Planner
- Interview Flow
- Conversation Memory
- Feedback Generator
- Frontend integration
- Deployment

---

## Development Principles

- Keep the solution simple.
- No authentication.
- No database unless required.
- Prompt-first development.
- Modular backend.
- Demo-ready over feature-heavy.

---

## Notes

Current backend provides only the application foundation.
No interview logic has been implemented yet.