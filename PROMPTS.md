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

