# Vercel entrypoint: Vercel serves the ASGI `app` exported here.
from app.main import app  # noqa: F401
