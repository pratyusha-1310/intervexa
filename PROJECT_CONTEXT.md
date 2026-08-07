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

### Candidate & Curriculum Loading

- Official `candidates.json` integrated.
- Official `curriculum.json` integrated.
- Added dedicated loader package (`app/loaders`).
- Implemented JSON validation and custom exceptions.
- Added unit tests for loader functionality.

Current interview logic has **not** been implemented yet.

# INTERVEXA – Project Context

## Current Architecture

```
Official Curriculum JSON
        +
Official Candidates JSON
        │
        ▼
Candidate Loader
        +
Curriculum Loader
        │
        ▼
Interview Planner
        │
        ▼
Interview Engine (Pending)
        │
        ▼
Conversation State (Pending)
        │
        ▼
Feedback Generator (Pending)
        │
        ▼
POST /api/interview
```

---

## Completed Milestones

### ✅ B0 – Repository Setup

- Repository initialized.
- Documentation created.
- GitHub configured.

### ✅ B1 – Backend Foundation

Implemented:

- FastAPI scaffold
- Configuration
- Health endpoint
- Project structure
- Environment configuration
- Unit tests

### ✅ B2 – Candidate & Curriculum Loading

Implemented:

- Candidate Loader
- Curriculum Loader
- JSON validation
- Custom exception hierarchy
- Loader unit tests

Official data source:

```
backend/data/
├── candidates.json
└── curriculum.json
```

### ✅ B3 – Adaptive Interview Planner

Implemented:

- InterviewPlan model
- Adaptive curriculum day selection
- Priority-based mission ranking
- Difficulty estimation
- Question budgeting (minimum 8)
- Curriculum metadata preservation
- Evaluation goal generation
- Interview strategy generation

The planner consumes:

- Official curriculum.json
- Official candidates.json

The planner does NOT:

- Generate interview questions
- Evaluate answers
- Produce feedback
- Call an LLM

---

## Official Technical Specification

Backend must expose:

```
POST /api/interview
```

Interview flow:

- Initial request includes:
  - sessionId
  - candidate object

Subsequent requests include:

- sessionId
- message

Final response returns:

- reply
- done
- structured feedback

---

## Backend Responsibilities

- Candidate loading
- Curriculum loading
- Interview planning
- Interview engine
- Conversation state
- Adaptive follow-ups
- Feedback generation
- API implementation

Frontend remains responsible only for presentation and interaction.

---

## Current Status

Completed:

- ✅ Repository Setup
- ✅ Backend Foundation
- ✅ Candidate & Curriculum Loading
- ✅ Interview Planner

Current Milestone:

➡️ B4 – Interview Engine

Pending:

- Interview Engine
- Conversation Memory
- Feedback Generator
- API Endpoint
- Frontend Integration
- Deployment

Interview Session Manager completed.

Capabilities:

- Session lifecycle

- Question progression

- Day progression

- Conversation history

- Completion tracking

No AI behaviour yet.

### ✅ B4C – AI Interview Agent

Implemented:

- AI Interview Agent
- Centralized interviewer system prompt
- Provider abstraction
- Mock LLM provider
- OpenAI provider
- Structured AgentResponse model
- Prompt construction
- Unit tests

The Interview Agent consumes:

- InterviewPlan
- InterviewSession
- InterviewDecision

The Interview Agent is responsible only for generating interviewer responses.

Business logic remains in the Planner, Session Manager, and Decision Engine.

Current supported providers:

- MockLLMProvider
- OpenAILLMProvider

Future providers (planned):

- Breeth Provider

The Interview Agent returns structured responses suitable for the API layer.