"""
Auditex -- FastAPI application factory.
Phase 6: registers all v1 routers, middleware, and lifespan events.
"""
import logging
import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Auditex starting -- environment: %s", settings.ENVIRONMENT)

    # Run DB migrations (alembic upgrade head -- idempotent)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd="/app",
        )
        if result.returncode == 0:
            logger.info("DB migrations: OK")
        else:
            logger.error("DB migrations failed:\n%s", result.stderr)
    except Exception as e:
        logger.error("DB migrations error: %s", e)

    yield

    logger.info("Auditex shutting down")


app = FastAPI(
    title="Auditex",
    description="AI Workflow Compliance Platform -- PoC Engine",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS -- development only; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
from app.api.v1 import health, tasks, agents, reports  # noqa: E402

app.include_router(health.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


# Root redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Auditex API -- see /docs"}
