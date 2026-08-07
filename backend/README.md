# Intervexa API

> Production-ready FastAPI backend scaffold for the **Intervexa** hackathon project.

---

## Project Structure

```
backend/
├── app/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # Pydantic-settings config (reads from .env)
│   ├── models/                # SQLAlchemy / ODM models (add as needed)
│   │   └── __init__.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── core.py            # GET /  and  GET /health
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── common.py          # Pydantic response models
│   ├── services/              # Business logic layer (add as needed)
│   │   └── __init__.py
│   ├── utils/                 # Shared helpers (add as needed)
│   │   └── __init__.py
│   ├── __init__.py
│   └── main.py                # App factory + lifespan + middleware
├── tests/
│   ├── __init__.py
│   └── test_core.py           # Smoke tests for core endpoints
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1 – Prerequisites

- Python **3.12+**
- (Recommended) a virtual environment

### 2 – Install dependencies

```bash
# From the backend/ directory
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3 – Configure environment

```bash
cp .env.example .env
# Edit .env as needed
```

### 4 – Run the development server

```bash
uvicorn app.main:app --reload
```

The API will be live at **http://localhost:8000**.

| URL | Description |
|-----|-------------|
| `GET /` | Service identity |
| `GET /health` | Liveness probe |
| `GET /docs` | Swagger UI |
| `GET /redoc` | ReDoc UI |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Extending the Project

| What to add | Where |
|-------------|-------|
| New endpoints | `app/routers/<feature>.py` → include in `main.py` |
| Business logic | `app/services/<feature>.py` |
| Request / response types | `app/schemas/<feature>.py` |
| ORM / ODM models | `app/models/<feature>.py` |
| Shared helpers | `app/utils/<feature>.py` |
| New config keys | `app/config/settings.py` + `.env.example` |

---

## Tech Stack

| Layer | Library |
|-------|---------|
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Testing | pytest + httpx |
