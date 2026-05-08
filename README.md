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
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python FastAPI (async) |
| LLM | Anthropic Claude (claude-sonnet-4-20250514 / claude-haiku-3-5-20241022) |
| Database | PostgreSQL (SQLAlchemy async + Alembic) |
| Cache/Queue | Redis (aioredis) |
| Validation | Pydantic v2 (backend), Zod (frontend), jsonschema |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API key

### Setup

```bash
# Clone the repo
git clone <repo-url> && cd appcompiler

# Set environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Start all services
docker-compose up --build

# Access the app
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Run Without Docker

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/generate` | Start a generation job |
| GET | `/api/status/{job_id}` | Get job status |
| GET | `/api/status/{job_id}/stream` | SSE stream of pipeline progress |
| GET | `/api/result/{job_id}` | Get full schema result |
| GET | `/api/result/{job_id}/download` | Download generated project as ZIP |
| POST | `/api/evaluate` | Run evaluation suite |
| GET | `/api/evaluate/{eval_id}/results` | Get evaluation results |
| GET | `/api/health` | Health check |

## Example Usage

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments"}'
```

## Evaluation Suite

AppCompiler includes 20 test prompts (10 real-world + 10 edge cases) for systematic evaluation:

```bash
# Run all 20 test prompts
curl -X POST http://localhost:8000/api/evaluate

# Run specific prompts
curl -X POST http://localhost:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"prompt_ids": ["prompt_1", "prompt_3"]}'
```

## Modes

- **Quality Mode** (default): Uses Claude Sonnet for all stages, full validation, TypeScript compile check
- **Fast Mode**: Uses Claude Haiku for early stages, skips refinement if clean, ~40% cheaper

## License

MIT
