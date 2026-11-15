from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.catalog_loader import get_catalog
from app.opt.content import get_content
from app.errors import register_error_handlers
from app.routers import assistant, auth, chat, checklist, me, profile, schools, tasks
from app.schemas.api import HealthResponse

# Load and validate the task catalog at import time so broken YAML fails the deploy, not a request.
CATALOG_TASK_COUNT = len(get_catalog().tasks)
OPT_TASK_COUNT = len(get_content().tasks)  # OPT content YAML, same fail-fast rule

app = FastAPI(title="Newcomer Navigator API", version=config.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, version=config.APP_VERSION, tasks=CATALOG_TASK_COUNT)


# Legacy newcomer endpoints (used by the mock frontend) + OPT MVP v1 contract (mock data).
for module in (profile, checklist, tasks, chat, auth, schools, me, assistant):
    app.include_router(module.router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """The UI lives in frontend/; the backend root points to the API docs."""
    return RedirectResponse("/docs")
