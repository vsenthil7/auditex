"""Auditex -- FastAPI Application. Phase 0 placeholder."""
from fastapi import FastAPI

app = FastAPI(title="Auditex", version="0.0.1")


@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.0.1",
        "phase": "Phase 0 -- scaffold only",
        "services": {
            "database": "not_connected",
            "redis": "not_connected",
            "vertex": "not_connected",
        },
    }
