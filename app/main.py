from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.errors import register_error_handlers
from app.routers import chat, checklist, profile, tasks

app = FastAPI(title="Newcomer Navigator API", version=config.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": config.APP_VERSION}


for module in (profile, checklist, tasks, chat):
    app.include_router(module.router)
