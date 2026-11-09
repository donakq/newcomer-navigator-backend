# Newcomer Navigator Backend

FastAPI backend for Newcomer Navigator, which helps new F-1 students in Washington State figure out which admin tasks they need to do (SSN, bank account, phone, ...), how to do them, and track their progress.

## Layout

```
api/index.py        Vercel entrypoint
app/main.py         FastAPI app, CORS, /api/health
app/routers/        profile, checklist, tasks, chat endpoints
app/schemas/        Pydantic models (the API contract)
app/services/       profile, rules engine, checklist, tasks, chat logic
app/ai/             LLM client, prompts, output validators
app/db/             SQLAlchemy models and session
catalog/            team-curated task YAML files and events.yaml
scripts/            offline scripts (official source ingestion, cleanup)
tests/
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Tests

```bash
pytest
```
