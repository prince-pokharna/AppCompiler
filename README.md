# AppCompiler — Natural Language to App Generator

A production-grade system that takes natural language descriptions and compiles them into validated, structured JSON schemas and working Next.js app scaffolds.

## How It Works

```
NL Input → Intent IR → Architecture → Schemas → Validation+Repair → Code Output
```

AppCompiler operates like a compiler with 6 stages:

1. **Intent Extraction** — Parses natural language into structured intent (app type, features, entities, roles)
2. **System Design** — Generates full architecture with entities, relations, pages, API groups, permissions
3. **Schema Generation** — Produces UI, API, DB, and Auth schemas in parallel
4. **Validation + Repair** — JSON Schema validation, cross-layer consistency checks, surgical repair
5. **Refinement** — Resolves remaining conflicts across schema layers
6. **Code Generation** — Generates a complete Next.js project with TypeScript checking

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | Python FastAPI (async) |
| LLM | OpenAI (`gpt-4o` / `gpt-4o-mini`) |
| Database | PostgreSQL (SQLAlchemy async + Alembic) — job persistence |
| Cache/Events | Redis (job cache, SSE event log, rate limits) |
| Validation | Pydantic v2 (backend), jsonschema |
| Prompts | Versioned Jinja2 templates (`backend/prompts/v1/`) |

## Security

All `/api/*` endpoints except `/api/health` require a Bearer token:

```bash
Authorization: Bearer <API_SECRET_KEY>
```

Set `API_SECRET_KEY` in `.env` (backend) and `NEXT_PUBLIC_API_KEY` in `.env` (frontend) to the same value.

## Trial (fastest path)

See **[TRIAL.md](TRIAL.md)** for step-by-step local trial instructions.

```powershell
.\setup.ps1    # once
.\start.ps1     # each session
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key

### Setup

```bash
git clone https://github.com/prince-pokharna/AppCompiler-.git
cd AppCompiler-

cp .env.example .env
# Edit .env: OPENAI_API_KEY, API_SECRET_KEY, NEXT_PUBLIC_API_KEY

docker-compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Run Without Docker

```bash
# Backend
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/generate` | Yes | Start a generation job |
| GET | `/api/status/{job_id}` | Yes | Get job status |
| GET | `/api/status/{job_id}/stream` | Yes | SSE pipeline progress |
| GET | `/api/result/{job_id}` | Yes | Full result + token usage |
| GET | `/api/result/{job_id}/download` | Yes | Download ZIP |
| POST | `/api/evaluate` | Yes | Run evaluation suite |
| GET | `/api/evaluate/{eval_id}/results` | Yes | Evaluation results |
| GET | `/api/health` | No | Health check |

## Example Usage

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_SECRET_KEY" \
  -d '{"prompt": "Build a CRM with login, contacts, dashboard, and role-based access"}'
```

## Testing

```bash
cd backend
pytest tests/ --cov=app --cov-report=term-missing
```

## Modes

- **Quality Mode** (default): `gpt-4o` for LLM stages, full validation
- **Fast Mode**: `gpt-4o-mini` for early stages, skips refinement when clean

## License

MIT
