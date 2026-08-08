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

### ✅ B5A – In-Memory Session Registry

Implemented:

- Session Registry
- Singleton registry accessor
- Session lifecycle management
- Duplicate session protection
- Session lookup
- Session removal
- Registry inspection utilities
- Unit tests

The Session Registry maintains active InterviewSession instances in memory.

It is intentionally lightweight and independent of FastAPI.

Future persistence mechanisms can replace the in-memory implementation without changing the backend architecture.

## ✅ B5B – Official Interview API

### Status

**Completed**

### Objective

Implemented the official hackathon API endpoint following the provided Technical Specification.

The backend now supports both:

- Interview initialization
- Interview continuation

through a single endpoint:

`POST /api/interview`

### New Components

- API request/response schemas
- Interview Controller
- Interview Router
- FastAPI route integration

### Implemented Features

- Official `POST /api/interview` endpoint
- Request validation
- Interview initialization flow
- Interview continuation flow
- Session Registry integration
- Interview Planner integration
- Interview Session integration
- Decision Engine integration
- AI Interview Agent integration
- Structured API responses
- HTTP exception handling
- Comprehensive integration tests

### Request Modes

#### Start Interview

```json
{
  "sessionId": "...",
  "candidate": { ... }
}
```

Flow:

- Load candidate
- Load curriculum
- Build InterviewPlan
- Create InterviewSession
- Register session
- Generate opening interviewer message
- Return API response

#### Continue Interview

```json
{
  "sessionId": "...",
  "message": "..."
}
```

Flow:

- Retrieve InterviewSession
- Store candidate response
- Invoke Decision Engine
- Generate next interviewer response
- Update session
- Return API response

### Response Format

During interview:

```json
{
  "reply": "...",
  "done": false
}
```

Interview completion:

```json
{
  "reply": "...",
  "done": true,
  "feedback": null
}
```

The Feedback Engine has not yet been integrated.

### Current Backend Architecture

```
Official JSON
        │
        ▼
Candidate & Curriculum Loaders
        │
        ▼
Interview Planner
        │
        ▼
Interview Session Manager
        │
        ▼
Interview Decision Engine
        │
        ▼
AI Interview Agent
        │
        ▼
Session Registry
        │
        ▼
Interview Controller
        │
        ▼
POST /api/interview
```

### Test Status

- 142 / 142 tests passing

### Current State

Backend API is now fully functional and ready for frontend integration.

The frontend can replace the mock InterviewService and begin consuming the official backend endpoint.

### Remaining Milestones

- B6A – Breeth LLM Provider
- B6B – Feedback Engine
- End-to-End Frontend Integration
- Production Deployment
- Final Testing & Submission

## ✅ B6A – Production LLM Provider (Gemini)

### Status

Completed

### Objective

Integrated Gemini as the production LLM provider using the official Google Gen AI SDK.

### Implemented

- GeminiLLMProvider
- Dynamic provider selection
- Environment-based configuration
- Graceful fallback
- Centralized provider management
- Gemini unit tests

### Environment Variables

```
LLM_PROVIDER
GEMINI_API_KEY
GEMINI_MODEL
```

### Current Provider Architecture

```
BaseLLMProvider
        │
        ├── MockLLMProvider
        ├── OpenAILLMProvider
        └── GeminiLLMProvider
```

The Interview Agent remains provider-agnostic and communicates only through the BaseLLMProvider interface.

### Test Status

151 / 151 tests passing

## ✅ B6B – Structured Feedback Engine

### Status

Completed

### Objective

Implemented the final Interview Feedback Engine and integrated it into the official interview API.

### Implemented

- InterviewFeedback schema
- Feedback generation service
- Structured JSON feedback
- Provider-agnostic generation
- Controller integration
- Robust fallback responses
- JSON sanitisation
- Updated API response
- Unit tests

### API Completion Response

The backend now returns:

```json
{
  "reply": "...",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": [],
    "gaps": [],
    "next": [],
    "technical_understanding": "...",
    "reasoning": "...",
    "communication": "...",
    "overall_assessment": "..."
  }
}
```

### Current Backend Architecture

```
Candidate Loader
        │
Curriculum Loader
        │
Interview Planner
        │
Interview Session
        │
Decision Engine
        │
Gemini Provider
        │
Interview Agent
        │
Feedback Engine
        │
Session Registry
        │
Interview Controller
        │
POST /api/interview
```

### Test Status

All automated tests passing.

Backend feature development is complete.

Remaining work focuses on frontend integration, end-to-end validation, deployment, and final submission.

## B5B Integration Fix – Candidate Payload Source of Truth

### Status

Completed

### Issue

Frontend integration exposed a mismatch between the frontend candidate dataset and the backend local `candidates.json`.

The official API specification requires the frontend to send the complete candidate object when starting an interview.

### Resolution

The backend now:

- validates the supplied candidate profile
- uses the supplied candidate object directly
- preserves the supplied candidate ID
- does not require the ID to exist in `backend/data/candidates.json`

The local candidate dataset remains useful for backend development and testing but is not a dependency of the official interview-start API.

### Architecture

```text
Frontend Candidate
        |
        v
POST /api/interview
        |
        v
Candidate Profile Validation
        |
        v
Interview Planner
        |
        v
Interview Session

## B6B Integration Fix – Duplicate Question Prevention

### Status

Completed

### Issue

During frontend E2E testing, the backend returned the exact same interviewer question after a candidate response.

### Root Cause

Short/evasive responses could repeatedly trigger FOLLOW_UP for the same question. The LLM provider could also return an identical interviewer response without backend duplicate detection.

### Resolution

Implemented two safeguards:

1. Follow-up limit:
   - Maximum one follow-up per planned question.
   - Subsequent turns progress toward the next curriculum question/topic.

2. Duplicate response protection:
   - Detects exact duplicate interviewer replies.
   - Retries generation once.
   - Uses a deterministic curriculum-based fallback if duplication persists.

### Files Changed

- `app/services/interview_decision_engine.py`
- `app/services/interview_agent.py`
- `tests/test_duplicate_prevention.py`

### Verification

163 / 163 tests passing.

### Integration Requirement

The frontend must be retested with a complete interview after pulling this backend fix.

The interview must contain:

- at least 8 genuine interviewer questions
- at least 4 curriculum days
- appropriate follow-ups
- maintained conversation context
- structured final feedback