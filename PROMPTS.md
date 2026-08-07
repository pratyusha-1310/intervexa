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