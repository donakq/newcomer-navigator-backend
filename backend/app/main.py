from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.errors import register_error_handlers
from app.opt.content import get_content
from app.routers import assistant, auth, me, schools
from app.schemas.opt import HealthResponse

# Load and validate the OPT content YAML at import time so broken YAML fails the deploy, not a request.
OPT_TASK_COUNT = len(get_content().tasks)

app = FastAPI(title="Paperwork Navigator API", version=config.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, version=config.APP_VERSION, tasks=OPT_TASK_COUNT)


for module in (auth, schools, me, assistant):
    app.include_router(module.router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """The UI lives in frontend/; the backend root points to the API docs."""
    return RedirectResponse("/docs")
