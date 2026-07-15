# Agentic RAG App

A multi-tenant "chat over your own documents" app. Each user has a private document library; an LLM agent decides for itself when a question needs a document lookup, grounds its answer in what it finds, cites sources, and streams the response live — resumable across refreshes and disconnects.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (sync) + async engine for chat sessions, Alembic
- **Agent**: [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) via OpenRouter (LLM + embeddings)
- **Auth**: Keycloak (JWT)
- **Storage**: MinIO (documents), Postgres (users/threads/documents + chat session history), Qdrant (vector search), Redis (cache, job queue, per-turn streaming)
- **Frontend**: React + TypeScript (Vite)
- **Tests**: pytest, against real local Postgres/Qdrant/MinIO/Keycloak with only the OpenRouter LLM/embedding calls faked

## Architecture at a glance

- **Documents are per-user, not per-thread.** Upload once; every conversation you have can search your whole library.
- **Retrieval is a tool, not a hardcoded step.** The agent decides per-message whether a document lookup is needed.
- **Owner isolation is enforced at the query level** (Postgres filters, Qdrant payload filters) — never post-hoc.
- **Chat generation runs in the background**, decoupled from the SSE connection: a turn keeps generating and persists to Postgres even if you close the tab, and a reconnecting client resumes exactly where it left off via Redis Streams + `Last-Event-ID`.

## Prerequisites

- Python 3.11+ and a virtualenv
- Node.js 18+
- Docker + Docker Compose
- An [OpenRouter](https://openrouter.ai/) API key

## Setup

### 1. Start infrastructure

```bash
docker compose up -d
```

This starts Postgres, Redis, MinIO, Qdrant, and Keycloak.

### 2. Configure Keycloak

```bash
python scripts/setup_keycloak.py --create-user <username> <password>
```

Creates the realm/client and (optionally) a test user. Re-runnable; skips anything that already exists.

### 3. Environment variables

Create `.env` (repo root), `backend/.env`, and `frontend/.env`. Variable names used:

**Root `.env`** — `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `DATABASE_URL`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `REDIS_URL`, `QDRANT_URL`, `QDRANT_COLLECTION`, `EMBEDDING_DIM`

**`backend/.env`** — `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_EMBEDDING_MODEL`, `OPENROUTER_AGENT_MODEL` (default `deepseek/deepseek-v4-pro`)

Optional tuning (all have sane defaults): `AGENT_SESSION_DATABASE_URL`, `RAG_TOOL_TOP_K`, `RAG_MIN_SCORE`, `CHAT_STREAM_TTL_SECONDS`, `CHAT_ACTIVE_TURN_TTL_SECONDS`, `CHAT_STREAM_BLOCK_MS`

**`frontend/.env`** — `VITE_API_BASE_URL`, `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`

### 4. Install dependencies

```bash
python -m venv venv
./venv/Scripts/activate        # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

cd frontend
npm install
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Run everything

```bash
# Backend API
uvicorn backend.main:app --reload --port 8000

# Document ingestion worker (separate process)
python -m backend.worker

# Frontend
cd frontend
npm run dev
```

Open http://localhost:5173.

## Running tests

```bash
pytest
```

Runs against real local Postgres/Qdrant/MinIO/Keycloak (isolated test database/bucket/collection, seeded Keycloak test users) — only OpenRouter calls are mocked. See `tests/unit/` and `tests/integration/`.

## Project layout

```
backend/
  agents/       agent, tools, streaming, session, citations — the agentic chat layer
  api/v1/       FastAPI routers/endpoints
  core/         config, auth, cache, redis client
  db/           models, repository, sync + async sessions
  rag/          chunking, extraction, embeddings, vector store
  storage/      MinIO client + repository
  worker.py     document ingestion job consumer
frontend/src/
  api/          typed API client
  components/   chat, document upload, search, thread list
scripts/        Keycloak setup, test token helper
tests/          unit + integration test suite
```
