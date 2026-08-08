## Prompt 1 – Backend Foundation

### Prompt
Create a production-ready backend foundation for a hackathon project called "Intervexa".

Tech Stack:
- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- Modular architecture

Requirements:
1. Generate only the project scaffold. Do NOT implement interview logic or AI features.
2. Create this structure:

backend/
│
├── app/
│   ├── routers/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── utils/
│   ├── config/
│   ├── __init__.py
│   └── main.py
│
├── tests/
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md

3. Configure FastAPI.
4. Add:
   - GET /
     Returns:
     {
       "service": "Intervexa API",
       "status": "running"
     }

   - GET /health
     Returns:
     {
       "status": "healthy"
     }

5. Organize imports cleanly.
6. Include instructions to run:
   uvicorn app.main:app --reload

Do not add:
- AI logic
- Candidate loader
- Curriculum loader
- Memory
- Feedback generator
- Database
- Authentication

### Generated
- FastAPI backend scaffold
- Modular project structure
- Root endpoint (`GET /`)
- Health endpoint (`GET /health`)
- Swagger/OpenAPI configuration
- Tests for root and health endpoints
- Configuration using pydantic-settings

### Verification
- Dependencies installed successfully
- Tests passed (2/2)
- Uvicorn server started successfully
- Swagger UI verified
- GET / verified
- GET /health verified

### Changes After Generation
- None

## Prompt 02 – Candidate & Curriculum Loaders

### Goal
Generate robust data loaders for the official hackathon JSON files.

### Tool
Antigravity

### Prompt
You are continuing the backend development of INTERVEXA.

Current milestone:
B2 — Candidate & Curriculum Loading

IMPORTANT:
Do NOT implement interview logic.
Do NOT implement AI.
Do NOT generate interview questions.
Do NOT generate conversation memory.
Do NOT generate planning logic.

Generate ONLY data loading utilities.

Project structure already exists.

Create:

app/loaders/
    __init__.py
    candidate_loader.py
    curriculum_loader.py

Requirements

1. candidate_loader.py

- Load backend/data/candidates.json
- Parse the JSON safely
- Validate the file exists
- Raise meaningful exceptions for:
    - missing file
    - invalid JSON
    - missing "candidates" key
- Return the candidate collection.

Expose:

load_candidates()

get_candidate(candidate_id)

2. curriculum_loader.py

- Load backend/data/curriculum.json
- Validate file existence
- Validate JSON
- Return curriculum data

Expose:

load_curriculum()

3. Keep paths configurable using pathlib.

4. Use type hints.

5. Keep the implementation simple and production-friendly.

6. Do NOT hardcode candidate data.

7. Do NOT modify the supplied JSON files.

8. Add concise docstrings.

9. Add basic unit tests for:
   - successful loading
   - missing file
   - invalid JSON

Return only the files required for this milestone.

### Result
- Created `app/loaders/`
- Added `candidate_loader.py`
- Added `curriculum_loader.py`
- Added JSON validation
- Added custom exception hierarchy
- Added unit tests

### Decision
Separated data loading from business logic by introducing a dedicated `loaders` package.

## Prompt 003 – Adaptive Interview Planner

### Goal

Generate the Interview Planner for INTERVEXA.

The planner should analyze the official candidate profile and curriculum data to create an internal interview strategy before the interview begins.

The planner must:

- Select at least 4 curriculum days.
- Plan for a minimum of 8 interview questions.
- Prioritize skipped missions and higher-attempt missions.
- Determine an initial interview difficulty based on the candidate profile.
- Generate evaluation goals and interview strategy.
- Preserve curriculum metadata for later use by the Interview Engine.

The planner must NOT:

- Generate interview questions.
- Call any LLM.
- Generate feedback.
- Implement API routes.
- Maintain conversation state.

### Tool

Antigravity

### Prompt

Generated an Interview Planner using the official `curriculum.json` and `candidates.json` schema.

The planner creates an internal `InterviewPlan` object containing:

- Selected curriculum days
- Selected modules
- Question allocation
- Initial difficulty
- Evaluation goals
- Interview strategy
- Selection reasons

The planner preserves curriculum metadata (day, module, tools, objectives, type) for later consumption by the Interview Engine.

### Result

Generated:

- `app/services/interview_planner.py`
- `app/schemas/interview_plan.py`
- Comprehensive unit tests

Implemented:

- Deterministic planning
- Priority-based curriculum selection
- Difficulty estimation
- Question budgeting
- Curriculum metadata preservation
- Interview strategy generation

### Decision

The Interview Planner is an internal backend component.

It is not exposed to the frontend.

It will later be consumed by the Interview Engine during interview initialization through the official `POST /api/interview` workflow.

## Prompt 004 – Interview Session Manager

### Goal

Generate the Interview Session Manager for INTERVEXA.

The Interview Session Manager is responsible for managing the lifecycle and state of a single interview session.

It must:

- Initialize a new interview session from an existing InterviewPlan.
- Track interview progress.
- Track the current curriculum day.
- Track the current question number.
- Track completed curriculum days.
- Maintain lightweight conversation history.
- Determine whether the interview has completed.

The Session Manager must NOT:

- Generate interview questions.
- Evaluate candidate answers.
- Call an LLM.
- Decide follow-up questions.
- Generate feedback.
- Expose API endpoints.

### Tool

Antigravity

### Prompt

Generated an Interview Session Manager that consumes an existing InterviewPlan and manages interview state throughout the interview lifecycle.

The implementation provides:

- InterviewSessionState schema
- InterviewSession service
- Session lifecycle management
- Question progression
- Curriculum day progression
- Conversation history
- Interview completion detection

Conversation history is intentionally lightweight and stores only structured conversation entries for later consumption by downstream components.

### Result

Generated:

- `app/services/interview_session.py`
- `app/schemas/interview_session.py`
- Comprehensive unit tests

Implemented:

- Session initialization
- Session state management
- State machine (Created → Active → Completed)
- Question budget enforcement
- Curriculum day progression
- Conversation history storage
- Interview completion tracking
- Custom exception hierarchy
- Full unit test coverage

### Decision

The Interview Session Manager is an internal backend component.

It consumes the InterviewPlan generated by the Interview Planner.

It manages interview state only.

It does not contain AI behaviour, business decisions, or interview generation logic.

Future components including the Decision Engine, LLM Question Generator, and Feedback Engine will consume the Interview Session Manager rather than modifying interview state directly.

## Prompt 006 – AI Interview Agent

### Goal

Generate the AI Interview Agent for INTERVEXA.

The AI Interview Agent is the only backend component responsible for communicating with the configured Large Language Model (LLM).

It must:

- Consume the InterviewPlan, InterviewSession, and InterviewDecision.
- Generate exactly one interviewer response at a time.
- Generate opening questions, follow-up questions, topic transitions, and interview completion messages.
- Return structured responses suitable for the API layer.
- Use a provider abstraction so the underlying LLM can be replaced without changing business logic.

The AI Interview Agent must NOT:

- Generate final interview feedback.
- Modify interview state.
- Expose API endpoints.
- Implement session management.
- Contain interview planning logic.

### Tool

Antigravity

### Prompt

Generated an AI Interview Agent with a centralized system prompt, provider abstraction, and structured response model.

Implemented:

- BaseLLMProvider abstraction
- MockLLMProvider for deterministic testing
- OpenAILLMProvider
- AgentResponse schema
- Prompt builder
- Structured response generation

Configuration is read from environment variables to support different LLM providers.

### Result

Generated:

- `app/services/interview_agent.py`
- `app/schemas/interview_agent.py`
- Configuration updates
- Comprehensive unit tests

Implemented:

- Provider abstraction
- Centralized interviewer system prompt
- Structured response model
- Opening question generation
- Follow-up generation
- Topic transition generation
- Interview completion message generation
- Mock provider for offline testing

### Decision

The AI Interview Agent is the only backend component allowed to communicate with an LLM.

All future AI interactions will pass through this service.

Business logic remains separated into the Planner, Session Manager, and Decision Engine.

## Prompt 007 – In-Memory Session Registry

### Goal

Generate an in-memory Session Registry for INTERVEXA.

The Session Registry is responsible for storing and managing active interview sessions.

It must:

- Create new sessions.
- Retrieve sessions by session ID.
- Check session existence.
- Remove completed sessions.
- Clear active sessions.
- Provide lightweight inspection for debugging.

The Session Registry must NOT:

- Implement API routes.
- Generate interview questions.
- Call an LLM.
- Implement interview logic.

### Tool

Antigravity

### Prompt

Generated an in-memory Session Registry using a lightweight singleton service.

Implemented:

- Session storage
- O(1) session lookup
- Duplicate session protection
- Session lifecycle management
- Singleton accessor

### Result

Generated:

- `app/services/session_registry.py`
- Comprehensive unit tests

Implemented:

- Session creation
- Session retrieval
- Session removal
- Session existence checks
- Active session count
- Session listing
- Registry clearing
- Custom exception hierarchy

### Decision

The Session Registry is the single source of truth for active interview sessions.

Future persistence layers (Redis/database) can replace the in-memory implementation without affecting the API or business logic.

## Prompt 008 – Official Interview API

### Goal

Implement the official hackathon API endpoint for INTERVEXA.

The endpoint must follow the provided Technical Specification exactly:

`POST /api/interview`

It must support both interview initialization and interview continuation while reusing the existing backend architecture.

The API layer should remain lightweight, delegating orchestration to a dedicated controller rather than containing business logic.

### Tool

Antigravity

### Prompt

Generated the official Interview API by connecting the existing backend components through an Interview Controller.

The implementation reuses:

- Candidate Loader
- Curriculum Loader
- Interview Planner
- Interview Session Manager
- Interview Decision Engine
- AI Interview Agent
- Session Registry

The controller orchestrates interview initialization and continuation while the FastAPI router remains a thin transport layer.

### Result

Generated:

- `app/schemas/interview_api.py`
- `app/services/interview_controller.py`
- `app/routers/interview.py`

Updated:

- `app/main.py`

Implemented:

- Official `POST /api/interview` endpoint
- Request validation for Start Interview and Continue Interview modes
- InterviewController orchestration layer
- Session Registry integration
- Interview Session lifecycle management
- AI Interview Agent integration
- Decision Engine integration
- Structured API responses
- HTTP exception mapping (400, 404, 409, 500)
- Comprehensive API and integration tests

### Decision

The API layer is intentionally thin.

Business logic remains encapsulated inside the Interview Controller and existing backend services.

The endpoint conforms to the official hackathon Technical Specification while keeping interview planning, session management, decision making, AI interaction, and session storage as independent components.

Final interview feedback is intentionally deferred to the Feedback Engine milestone and currently returns `null` when the interview completes.

## Prompt 009 – Production LLM Provider (Gemini)

### Goal

Integrate Google's Gemini API as the production LLM provider while preserving the existing provider abstraction.

The Interview Agent should continue interacting only through the BaseLLMProvider interface.

Support dynamic provider selection using environment variables.

### Tool

Antigravity

### Prompt

Generated a production-ready Gemini provider using the official Google Gen AI SDK.

Implemented:

- GeminiLLMProvider
- Dynamic provider selection
- Environment-based configuration
- Error handling
- SDK integration
- Unit tests

### Result

Updated:

- `app/services/interview_agent.py`
- `app/config/settings.py`

Generated:

- Gemini provider implementation
- Provider selection logic
- Gemini unit tests

Implemented:

- Official Google Gen AI SDK integration
- Dynamic provider selection
- Configuration via `.env`
- Graceful fallback to Mock provider
- Robust exception handling

### Decision

Gemini is now the primary production LLM provider.

The provider architecture remains modular, allowing future providers (OpenAI, Anthropic, Groq, OpenRouter, etc.) to be added without modifying the Interview Agent.

## Prompt 010 – Structured Feedback Engine

### Goal

Implement the final structured interview feedback engine for INTERVEXA.

The feedback should be generated when an interview concludes and returned through the official `POST /api/interview` endpoint.

The implementation should remain provider-agnostic and reuse the existing LLM abstraction.

### Tool

Antigravity

### Prompt

Generated a structured Interview Feedback Engine using the existing provider abstraction.

Implemented:

- InterviewFeedback schema
- Feedback generation service
- Controller integration
- Robust fallback handling
- JSON extraction & sanitisation
- Unit tests

### Result

Generated:

- `app/schemas/interview_feedback.py`
- `app/services/interview_feedback.py`

Updated:

- `app/services/interview_controller.py`
- `app/schemas/interview_api.py`
- `app/services/interview_agent.py`

Implemented:

- Structured interview feedback
- Provider-agnostic feedback generation
- Safe fallback responses
- JSON sanitisation
- API integration
- Unit tests

### Decision

Feedback generation remains completely independent from the Interview Agent.

The Interview Controller orchestrates feedback generation only after interview completion, preserving clean separation of responsibilities while satisfying the hackathon requirement for structured interview evaluation.

## Prompt 011 – B5B Candidate Payload Integration Fix

### Goal

Fix the official POST /api/interview start flow so that the complete candidate object supplied by the frontend is used directly, as required by the official Technical Specification.

### Tool

Antigravity

### Prompt

Fixed an integration issue where the backend extracted a candidate ID from the start request and attempted an exact lookup in backend/data/candidates.json.

The official API contract supplies the complete candidate object in the request, so the supplied candidate profile must be the source of truth for that interview session.

The fix:

- validates the supplied candidate profile
- uses it directly for interview planning
- preserves the supplied candidate ID
- removes the dependency on an exact local dataset match
- preserves existing continue-interview behavior
- adds integration tests for custom and existing candidate IDs

### Result

Added:

- `app/schemas/candidate_profile.py`

Updated:

- `app/services/interview_controller.py`
- `tests/test_interview_api.py`

All 161 tests passed.

### Decision

The official API remains stateless with respect to candidate selection: the complete candidate profile supplied in the start request is authoritative for that interview.

The local `candidates.json` remains available for development and testing but is not required for a candidate ID to be accepted by `POST /api/interview`.