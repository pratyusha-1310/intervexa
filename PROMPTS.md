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